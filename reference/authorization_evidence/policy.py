"""Finite scope and budget containment. Apache-2.0."""
from .core import require, instant

def money(value):
    return value['asset'], value['network'], int(value['amount'])

def money_le(a, b):
    x, y = money(a), money(b)
    return x[:2] == y[:2] and x[2] <= y[2]

def covers(parent, child):
    return (parent['tool_id'] == child['tool_id'] and parent['version'] == child['version']
            and parent['operation'] == child['operation']
            and set(child['resources']) <= set(parent['resources'])
            and instant(parent['valid_from']) <= instant(child['valid_from'])
            and instant(child['expires_at']) <= instant(parent['expires_at'])
            and money_le(child['max_call_budget'], parent['max_call_budget']))

def within(rule, tool, invocation, at):
    return (rule['tool_id'] == tool['tool_id'] and rule['version'] == tool['version']
            and rule['operation'] == invocation['operation']
            and invocation['resource'] in rule['resources']
            and instant(rule['valid_from']) <= instant(at) < instant(rule['expires_at'])
            and money_le(invocation['budget'], rule['max_call_budget']))

def allowed(limits, tool, invocation, at):
    return (any(within(x, tool, invocation, at) for x in limits['allow'])
            and not any(within(x, tool, invocation, at) for x in limits['deny']))

def narrow(child, parent, strict=False):
    require(money_le(child['total_budget'], parent['total_budget']), 'UNAUTHORIZED', 'total budget widens')
    require(all(any(covers(p, c) for p in parent['allow']) for c in child['allow']),
            'UNAUTHORIZED', 'scope coverage widens')
    # Conservative exact parent-deny preservation. More complex equivalent sets are unsupported.
    require(all(x in child['deny'] for x in parent['deny']),
            'UNAUTHORIZED', 'parent deny removed')
    if strict:
        if money(child['total_budget'])[2] < money(parent['total_budget'])[2]:
            return
        # Exact finite witness search for this supported upper-bound/interval/set grammar.
        # Splitting/reordering equal scopes must not manufacture "strict" narrowing.
        rules = parent['allow'] + parent['deny'] + child['allow'] + child['deny']
        times = {r[k] for r in rules for k in ('valid_from', 'expires_at')}
        for rule in parent['allow']:
            tool = {'tool_id': rule['tool_id'], 'version': rule['version']}
            asset, network, ceiling = money(rule['max_call_budget'])
            amounts = {0, ceiling}
            amounts |= {money(r['max_call_budget'])[2] + 1 for r in rules
                        if money(r['max_call_budget'])[:2] == (asset, network)}
            for resource in rule['resources']:
                for at in times:
                    for amount in amounts:
                        if amount > ceiling:
                            continue
                        inv = {'operation': rule['operation'], 'resource': resource,
                               'budget': {'asset': asset, 'network': network, 'amount': str(amount)}}
                        if allowed(parent, tool, inv, at) and not allowed(child, tool, inv, at):
                            return
        require(False, 'UNAUTHORIZED', 'no strict authority reduction established')
