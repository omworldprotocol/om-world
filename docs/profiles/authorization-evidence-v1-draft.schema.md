# Authorization/evidence v1-draft revision 2 — structural JSON Schema

CC-BY-4.0 specification material. Shape checks do not verify cryptography or authority. See [closure rules](authorization-evidence-dependency-closure.md).

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://omworldprotocol.github.io/om-world/schemas/authorization-evidence-v1-draft.json",
  "title": "Authorization/evidence v1-draft structural schema; not an implementation qualification",
  "oneOf": [
    {
      "$ref": "#/$defs/Intent"
    },
    {
      "$ref": "#/$defs/Acceptance"
    },
    {
      "$ref": "#/$defs/Consent"
    },
    {
      "$ref": "#/$defs/InvocationApproval"
    },
    {
      "$ref": "#/$defs/Invocation"
    },
    {
      "$ref": "#/$defs/DependencyManifest"
    },
    {
      "$ref": "#/$defs/ToolEntry"
    },
    {
      "$ref": "#/$defs/DeploymentPolicy"
    },
    {
      "$ref": "#/$defs/Plan"
    },
    {
      "$ref": "#/$defs/ContextManifest"
    },
    {
      "$ref": "#/$defs/Configuration"
    },
    {
      "$ref": "#/$defs/CustodyProfile"
    },
    {
      "$ref": "#/$defs/EvidenceBundle"
    },
    {
      "$ref": "#/$defs/IdentityProfile"
    },
    {
      "$ref": "#/$defs/ConfirmationProfile"
    },
    {
      "$ref": "#/$defs/EvidenceProfile"
    },
    {
      "$ref": "#/$defs/BudgetProfile"
    },
    {
      "$ref": "#/$defs/RelayProfile"
    },
    {
      "$ref": "#/$defs/RestrictionProfile"
    },
    {
      "$ref": "#/$defs/CustodyAccessProfile"
    },
    {
      "$ref": "#/$defs/RegistrySnapshot"
    },
    {
      "$ref": "#/$defs/ToolBehavior"
    },
    {
      "$ref": "#/$defs/Delegation"
    },
    {
      "$ref": "#/$defs/KeyEvent"
    },
    {
      "$ref": "#/$defs/ChannelReceipt"
    },
    {
      "$ref": "#/$defs/FinalityRule"
    },
    {
      "$ref": "#/$defs/RelayReceipt"
    },
    {
      "$ref": "#/$defs/BudgetEvent"
    }
  ],
  "$defs": {
    "Ref": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "object_type": {
          "type": "string",
          "minLength": 1
        },
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        }
      },
      "required": [
        "id",
        "object_type",
        "profile"
      ],
      "additionalProperties": false
    },
    "ArtifactRef": {
      "type": "object",
      "properties": {
        "digest": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "media_type": {
          "type": "string",
          "minLength": 1
        }
      },
      "required": [
        "digest",
        "media_type"
      ],
      "additionalProperties": false
    },
    "Money": {
      "type": "object",
      "properties": {
        "asset": {
          "type": "string",
          "minLength": 1
        },
        "network": {
          "type": "string",
          "minLength": 1
        },
        "amount": {
          "type": "string",
          "pattern": "^(0|[1-9][0-9]*)$"
        }
      },
      "required": [
        "asset",
        "network",
        "amount"
      ],
      "additionalProperties": false
    },
    "Signature": {
      "type": "object",
      "properties": {
        "scheme": {
          "const": "Ed25519-RFC8032-pure-over-sha256-digest"
        },
        "key_ref": {
          "$ref": "#/$defs/ArtifactRef"
        },
        "value": {
          "type": "string",
          "pattern": "^[0-9a-f]{128}$"
        }
      },
      "required": [
        "scheme",
        "key_ref",
        "value"
      ],
      "additionalProperties": false
    },
    "Action": {
      "type": "object",
      "properties": {
        "tool_id": {
          "type": "string",
          "minLength": 1
        },
        "version": {
          "type": "string",
          "minLength": 1
        },
        "operation": {
          "type": "string",
          "minLength": 1
        },
        "resources": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1
          },
          "minItems": 1
        },
        "valid_from": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "expires_at": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "max_call_budget": {
          "$ref": "#/$defs/Money"
        }
      },
      "required": [
        "tool_id",
        "version",
        "operation",
        "resources",
        "valid_from",
        "expires_at",
        "max_call_budget"
      ],
      "additionalProperties": false
    },
    "Limits": {
      "type": "object",
      "properties": {
        "allow": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/Action"
          },
          "minItems": 1
        },
        "deny": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/Action"
          },
          "minItems": 0
        },
        "total_budget": {
          "$ref": "#/$defs/Money"
        }
      },
      "required": [
        "allow",
        "deny",
        "total_budget"
      ],
      "additionalProperties": false
    },
    "Intent": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "Intent"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "principal": {
          "type": "string",
          "pattern": "^ed25519:[0-9a-f]{64}$"
        },
        "body": {
          "type": "string",
          "minLength": 1
        },
        "constraints": {
          "$ref": "#/$defs/Limits"
        },
        "success_criteria_ref": {
          "$ref": "#/$defs/ArtifactRef"
        },
        "evidence_requirements_ref": {
          "$ref": "#/$defs/ArtifactRef"
        },
        "nonce": {
          "type": "string",
          "minLength": 1
        },
        "issued_at": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "expires_at": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "signature": {
          "$ref": "#/$defs/Signature"
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "principal",
        "body",
        "constraints",
        "success_criteria_ref",
        "evidence_requirements_ref",
        "nonce",
        "issued_at",
        "expires_at",
        "signature"
      ],
      "additionalProperties": false
    },
    "Acceptance": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "Acceptance"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "intent_ref": {
          "allOf": [
            {
              "$ref": "#/$defs/Ref"
            },
            {
              "properties": {
                "object_type": {
                  "const": "Intent"
                }
              }
            }
          ]
        },
        "agent_root": {
          "type": "string",
          "pattern": "^ed25519:[0-9a-f]{64}$"
        },
        "signer_key_ref": {
          "$ref": "#/$defs/ArtifactRef"
        },
        "delegation_refs": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/ArtifactRef"
          },
          "minItems": 0
        },
        "plan_ref": {
          "allOf": [
            {
              "$ref": "#/$defs/Ref"
            },
            {
              "properties": {
                "object_type": {
                  "const": "Plan"
                }
              }
            }
          ]
        },
        "dependency_manifest_ref": {
          "allOf": [
            {
              "$ref": "#/$defs/Ref"
            },
            {
              "properties": {
                "object_type": {
                  "const": "DependencyManifest"
                }
              }
            }
          ]
        },
        "action_limits": {
          "$ref": "#/$defs/Limits"
        },
        "fee_quote": {
          "$ref": "#/$defs/Money"
        },
        "deadline": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "nonce": {
          "type": "string",
          "minLength": 1
        },
        "issued_at": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "expires_at": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "signature": {
          "$ref": "#/$defs/Signature"
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "intent_ref",
        "agent_root",
        "signer_key_ref",
        "delegation_refs",
        "plan_ref",
        "dependency_manifest_ref",
        "action_limits",
        "fee_quote",
        "deadline",
        "nonce",
        "issued_at",
        "expires_at",
        "signature"
      ],
      "additionalProperties": false
    },
    "Consent": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "Consent"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "principal": {
          "type": "string",
          "pattern": "^ed25519:[0-9a-f]{64}$"
        },
        "acceptance_ref": {
          "allOf": [
            {
              "$ref": "#/$defs/Ref"
            },
            {
              "properties": {
                "object_type": {
                  "const": "Acceptance"
                }
              }
            }
          ]
        },
        "dependency_manifest_ref": {
          "allOf": [
            {
              "$ref": "#/$defs/Ref"
            },
            {
              "properties": {
                "object_type": {
                  "const": "DependencyManifest"
                }
              }
            }
          ]
        },
        "action_limits": {
          "$ref": "#/$defs/Limits"
        },
        "nonce": {
          "type": "string",
          "minLength": 1
        },
        "issued_at": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "expires_at": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "signature": {
          "$ref": "#/$defs/Signature"
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "principal",
        "acceptance_ref",
        "dependency_manifest_ref",
        "action_limits",
        "nonce",
        "issued_at",
        "expires_at",
        "signature"
      ],
      "additionalProperties": false
    },
    "InvocationApproval": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "InvocationApproval"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "principal": {
          "type": "string",
          "pattern": "^ed25519:[0-9a-f]{64}$"
        },
        "acceptance_ref": {
          "allOf": [
            {
              "$ref": "#/$defs/Ref"
            },
            {
              "properties": {
                "object_type": {
                  "const": "Acceptance"
                }
              }
            }
          ]
        },
        "invocation_ref": {
          "allOf": [
            {
              "$ref": "#/$defs/Ref"
            },
            {
              "properties": {
                "object_type": {
                  "const": "Invocation"
                }
              }
            }
          ]
        },
        "dependency_manifest_ref": {
          "allOf": [
            {
              "$ref": "#/$defs/Ref"
            },
            {
              "properties": {
                "object_type": {
                  "const": "DependencyManifest"
                }
              }
            }
          ]
        },
        "approval_mode": {
          "enum": [
            "affirmative",
            "out_of_band"
          ]
        },
        "channel_evidence_ref": {
          "$ref": "#/$defs/ArtifactRef"
        },
        "nonce": {
          "type": "string",
          "minLength": 1
        },
        "issued_at": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "expires_at": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "signature": {
          "$ref": "#/$defs/Signature"
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "principal",
        "acceptance_ref",
        "invocation_ref",
        "dependency_manifest_ref",
        "approval_mode",
        "channel_evidence_ref",
        "nonce",
        "issued_at",
        "expires_at",
        "signature"
      ],
      "additionalProperties": false
    },
    "Invocation": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "Invocation"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "acceptance_ref": {
          "allOf": [
            {
              "$ref": "#/$defs/Ref"
            },
            {
              "properties": {
                "object_type": {
                  "const": "Acceptance"
                }
              }
            }
          ]
        },
        "plan_index": {
          "type": "integer",
          "minimum": 0
        },
        "tool_entry_ref": {
          "allOf": [
            {
              "$ref": "#/$defs/Ref"
            },
            {
              "properties": {
                "object_type": {
                  "const": "ToolEntry"
                }
              }
            }
          ]
        },
        "deployment_policy_ref": {
          "allOf": [
            {
              "$ref": "#/$defs/Ref"
            },
            {
              "properties": {
                "object_type": {
                  "const": "DeploymentPolicy"
                }
              }
            }
          ]
        },
        "operation": {
          "type": "string",
          "minLength": 1
        },
        "resource": {
          "type": "string",
          "minLength": 1
        },
        "input_ref": {
          "$ref": "#/$defs/ArtifactRef"
        },
        "budget": {
          "$ref": "#/$defs/Money"
        },
        "nonce": {
          "type": "string",
          "minLength": 1
        },
        "issued_at": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "acceptance_ref",
        "plan_index",
        "tool_entry_ref",
        "deployment_policy_ref",
        "operation",
        "resource",
        "input_ref",
        "budget",
        "nonce",
        "issued_at"
      ],
      "additionalProperties": false
    },
    "DependencyManifest": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "DependencyManifest"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "registry_snapshot_ref": {
          "$ref": "#/$defs/ArtifactRef"
        },
        "tool_entry_refs": {
          "type": "array",
          "items": {
            "allOf": [
              {
                "$ref": "#/$defs/Ref"
              },
              {
                "properties": {
                  "object_type": {
                    "const": "ToolEntry"
                  }
                }
              }
            ]
          },
          "minItems": 1
        },
        "deployment_policy_refs": {
          "type": "array",
          "items": {
            "allOf": [
              {
                "$ref": "#/$defs/Ref"
              },
              {
                "properties": {
                  "object_type": {
                    "const": "DeploymentPolicy"
                  }
                }
              }
            ]
          },
          "minItems": 1
        },
        "identity_profile_ref": {
          "$ref": "#/$defs/ArtifactRef"
        },
        "confirmation_profile_ref": {
          "$ref": "#/$defs/ArtifactRef"
        },
        "custody_profile_ref": {
          "allOf": [
            {
              "$ref": "#/$defs/Ref"
            },
            {
              "properties": {
                "object_type": {
                  "const": "CustodyProfile"
                }
              }
            }
          ]
        },
        "evidence_profile_ref": {
          "$ref": "#/$defs/ArtifactRef"
        },
        "budget_profile_ref": {
          "$ref": "#/$defs/ArtifactRef"
        },
        "relay_profile_ref": {
          "$ref": "#/$defs/ArtifactRef"
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "registry_snapshot_ref",
        "tool_entry_refs",
        "deployment_policy_refs",
        "identity_profile_ref",
        "confirmation_profile_ref",
        "custody_profile_ref",
        "evidence_profile_ref",
        "budget_profile_ref",
        "relay_profile_ref"
      ],
      "additionalProperties": false
    },
    "ToolEntry": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "ToolEntry"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "tool_id": {
          "type": "string",
          "minLength": 1
        },
        "version": {
          "type": "string",
          "minLength": 1
        },
        "provider": {
          "type": "string",
          "pattern": "^ed25519:[0-9a-f]{64}$"
        },
        "registrar": {
          "type": "string",
          "pattern": "^ed25519:[0-9a-f]{64}$"
        },
        "interface_ref": {
          "$ref": "#/$defs/ArtifactRef"
        },
        "behavior_ref": {
          "$ref": "#/$defs/ArtifactRef"
        },
        "operation_classes": {
          "type": "array",
          "items": {
            "enum": [
              "read",
              "write",
              "destructive",
              "admin"
            ]
          },
          "minItems": 1
        },
        "confirmation": {
          "enum": [
            "automatic",
            "human-in-loop",
            "restricted"
          ]
        },
        "boundary": {
          "enum": [
            "local",
            "relay",
            "public"
          ]
        },
        "stateful": {
          "type": "boolean"
        },
        "valid_from": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "signature": {
          "$ref": "#/$defs/Signature"
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "tool_id",
        "version",
        "provider",
        "registrar",
        "interface_ref",
        "behavior_ref",
        "operation_classes",
        "confirmation",
        "boundary",
        "stateful",
        "valid_from",
        "signature"
      ],
      "additionalProperties": false
    },
    "DeploymentPolicy": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "DeploymentPolicy"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "operator": {
          "type": "string",
          "pattern": "^ed25519:[0-9a-f]{64}$"
        },
        "revision": {
          "type": "string",
          "minLength": 1
        },
        "baseline_refs": {
          "type": "array",
          "items": {
            "allOf": [
              {
                "$ref": "#/$defs/Ref"
              },
              {
                "properties": {
                  "object_type": {
                    "const": "ToolEntry"
                  }
                }
              }
            ]
          },
          "minItems": 1
        },
        "deny_rules": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/Action"
          },
          "minItems": 0
        },
        "extra_requirements_ref": {
          "$ref": "#/$defs/ArtifactRef"
        },
        "valid_from": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "signature": {
          "$ref": "#/$defs/Signature"
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "operator",
        "revision",
        "baseline_refs",
        "deny_rules",
        "extra_requirements_ref",
        "valid_from",
        "signature"
      ],
      "additionalProperties": false
    },
    "Plan": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "Plan"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "ordered_actions": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "action": {
                "$ref": "#/$defs/Action"
              },
              "input_ref": {
                "$ref": "#/$defs/ArtifactRef"
              }
            },
            "required": [
              "action",
              "input_ref"
            ],
            "additionalProperties": false
          },
          "minItems": 1
        },
        "expected_artifact_descriptions": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1
          },
          "minItems": 0
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "ordered_actions",
        "expected_artifact_descriptions"
      ],
      "additionalProperties": false
    },
    "ContextManifest": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "ContextManifest"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "pre_state_refs": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/ArtifactRef"
          },
          "minItems": 0
        },
        "retrieval_procedure_refs": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/ArtifactRef"
          },
          "minItems": 0
        },
        "configuration_refs": {
          "type": "array",
          "items": {
            "allOf": [
              {
                "$ref": "#/$defs/Ref"
              },
              {
                "properties": {
                  "object_type": {
                    "const": "Configuration"
                  }
                }
              }
            ]
          },
          "minItems": 0
        },
        "provenance_refs": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/ArtifactRef"
          },
          "minItems": 1
        },
        "observed_at": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "pre_state_refs",
        "retrieval_procedure_refs",
        "configuration_refs",
        "provenance_refs",
        "observed_at"
      ],
      "additionalProperties": false
    },
    "Configuration": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "Configuration"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "config_bytes_ref": {
          "$ref": "#/$defs/ArtifactRef"
        },
        "provisioner": {
          "type": "string",
          "pattern": "^ed25519:[0-9a-f]{64}$"
        },
        "effective_from": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "effective_until": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "signature": {
          "$ref": "#/$defs/Signature"
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "config_bytes_ref",
        "provisioner",
        "effective_from",
        "effective_until",
        "signature"
      ],
      "additionalProperties": false
    },
    "CustodyProfile": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "CustodyProfile"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "custodian": {
          "type": "string",
          "pattern": "^ed25519:[0-9a-f]{64}$"
        },
        "evidence_classes": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1
          },
          "minItems": 1
        },
        "retention_until": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "access_policy_ref": {
          "$ref": "#/$defs/ArtifactRef"
        },
        "export_policy_ref": {
          "$ref": "#/$defs/ArtifactRef"
        },
        "mirror_refs": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/ArtifactRef"
          },
          "minItems": 0
        },
        "challenge_appeal_policy_ref": {
          "$ref": "#/$defs/ArtifactRef"
        },
        "signature": {
          "$ref": "#/$defs/Signature"
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "custodian",
        "evidence_classes",
        "retention_until",
        "access_policy_ref",
        "export_policy_ref",
        "mirror_refs",
        "challenge_appeal_policy_ref",
        "signature"
      ],
      "additionalProperties": false
    },
    "EvidenceBundle": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "EvidenceBundle"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "intent_ref": {
          "allOf": [
            {
              "$ref": "#/$defs/Ref"
            },
            {
              "properties": {
                "object_type": {
                  "const": "Intent"
                }
              }
            }
          ]
        },
        "acceptance_ref": {
          "allOf": [
            {
              "$ref": "#/$defs/Ref"
            },
            {
              "properties": {
                "object_type": {
                  "const": "Acceptance"
                }
              }
            }
          ]
        },
        "consent_refs": {
          "type": "array",
          "items": {
            "allOf": [
              {
                "$ref": "#/$defs/Ref"
              },
              {
                "properties": {
                  "object_type": {
                    "const": "Consent"
                  }
                }
              }
            ]
          },
          "minItems": 1,
          "maxItems": 1
        },
        "approval_refs": {
          "type": "array",
          "items": {
            "allOf": [
              {
                "$ref": "#/$defs/Ref"
              },
              {
                "properties": {
                  "object_type": {
                    "const": "InvocationApproval"
                  }
                }
              }
            ]
          },
          "minItems": 0
        },
        "dependency_manifest_ref": {
          "allOf": [
            {
              "$ref": "#/$defs/Ref"
            },
            {
              "properties": {
                "object_type": {
                  "const": "DependencyManifest"
                }
              }
            }
          ]
        },
        "invocation_refs": {
          "type": "array",
          "items": {
            "allOf": [
              {
                "$ref": "#/$defs/Ref"
              },
              {
                "properties": {
                  "object_type": {
                    "const": "Invocation"
                  }
                }
              }
            ]
          },
          "minItems": 1
        },
        "context_refs": {
          "type": "array",
          "items": {
            "allOf": [
              {
                "$ref": "#/$defs/Ref"
              },
              {
                "properties": {
                  "object_type": {
                    "const": "ContextManifest"
                  }
                }
              }
            ]
          },
          "minItems": 0
        },
        "aggregate_proof_ref": {
          "$ref": "#/$defs/ArtifactRef"
        },
        "exported_evidence_refs": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/ArtifactRef"
          },
          "minItems": 1
        },
        "step_bindings": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/StepBinding"
          },
          "minItems": 1
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "intent_ref",
        "acceptance_ref",
        "consent_refs",
        "approval_refs",
        "dependency_manifest_ref",
        "invocation_refs",
        "context_refs",
        "aggregate_proof_ref",
        "exported_evidence_refs",
        "step_bindings"
      ],
      "additionalProperties": false
    },
    "StepBinding": {
      "type": "object",
      "properties": {
        "step_index": {
          "type": "integer",
          "minimum": 0
        },
        "invocation_ref": {
          "allOf": [
            {
              "$ref": "#/$defs/Ref"
            },
            {
              "properties": {
                "object_type": {
                  "const": "Invocation"
                }
              }
            }
          ]
        },
        "context_refs": {
          "type": "array",
          "items": {
            "allOf": [
              {
                "$ref": "#/$defs/Ref"
              },
              {
                "properties": {
                  "object_type": {
                    "const": "ContextManifest"
                  }
                }
              }
            ]
          },
          "maxItems": 1
        },
        "input_ref": {
          "$ref": "#/$defs/ArtifactRef"
        },
        "output_ref": {
          "$ref": "#/$defs/ArtifactRef"
        },
        "step_digest": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        }
      },
      "required": [
        "step_index",
        "invocation_ref",
        "context_refs",
        "input_ref",
        "output_ref",
        "step_digest"
      ],
      "additionalProperties": false
    },
    "IdentityProfile": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "IdentityProfile"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "suite": {
          "const": "Ed25519-RFC8032-pure-over-sha256-digest"
        },
        "principal_keys": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^ed25519:[0-9a-f]{64}$"
          },
          "minItems": 1
        },
        "agent_root_keys": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^ed25519:[0-9a-f]{64}$"
          },
          "minItems": 1
        },
        "registrar_keys": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^ed25519:[0-9a-f]{64}$"
          },
          "minItems": 1
        },
        "operator_keys": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^ed25519:[0-9a-f]{64}$"
          },
          "minItems": 1
        },
        "provisioner_keys": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^ed25519:[0-9a-f]{64}$"
          },
          "minItems": 1
        },
        "custodian_keys": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^ed25519:[0-9a-f]{64}$"
          },
          "minItems": 1
        },
        "relayer_keys": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^ed25519:[0-9a-f]{64}$"
          },
          "minItems": 1
        },
        "delegation_artifact_refs": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/ArtifactRef"
          },
          "minItems": 0
        },
        "key_event_refs": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/ArtifactRef"
          },
          "minItems": 0
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "suite",
        "principal_keys",
        "agent_root_keys",
        "registrar_keys",
        "operator_keys",
        "provisioner_keys",
        "custodian_keys",
        "relayer_keys",
        "delegation_artifact_refs",
        "key_event_refs"
      ],
      "additionalProperties": false
    },
    "ConfirmationProfile": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "ConfirmationProfile"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "human_in_loop": {
          "const": "principal-affirmative-per-invocation"
        },
        "restricted": {
          "const": "principal-out-of-band-per-invocation"
        },
        "channel_authority_keys": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^ed25519:[0-9a-f]{64}$"
          },
          "minItems": 1
        },
        "channel_receipt_refs": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/ArtifactRef"
          },
          "minItems": 0,
          "maxItems": 0
        },
        "approval_reuse": {
          "const": "forbidden"
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "human_in_loop",
        "restricted",
        "channel_authority_keys",
        "channel_receipt_refs",
        "approval_reuse"
      ],
      "additionalProperties": false
    },
    "EvidenceProfile": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "EvidenceProfile"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "mapping": {
          "const": "linear-bijection-stepbindings-v1"
        },
        "payload_encoding": {
          "const": "RFC8785-JCS-IJSON"
        },
        "hash_encoding": {
          "const": "sha256-colon-lowerhex"
        },
        "subjective_evaluator_keys": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^ed25519:[0-9a-f]{64}$"
          },
          "minItems": 0
        },
        "subjective_result_refs": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/ArtifactRef"
          },
          "minItems": 0
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "mapping",
        "payload_encoding",
        "hash_encoding",
        "subjective_evaluator_keys",
        "subjective_result_refs"
      ],
      "additionalProperties": false
    },
    "BudgetProfile": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "BudgetProfile"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "mode": {
          "const": "single-deployment-atomic-reservation-required"
        },
        "deployment_id": {
          "type": "string",
          "minLength": 1
        },
        "ledger_authority_keys": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^ed25519:[0-9a-f]{64}$"
          },
          "minItems": 1
        },
        "ledger_protocol": {
          "const": "reserve-before-call-consume-or-release-v1"
        },
        "ledger_event_refs": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/ArtifactRef"
          },
          "minItems": 0
        },
        "cross_deployment": {
          "const": "unsupported"
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "mode",
        "deployment_id",
        "ledger_authority_keys",
        "ledger_protocol",
        "ledger_event_refs",
        "cross_deployment"
      ],
      "additionalProperties": false
    },
    "RelayProfile": {
      "oneOf": [
        {
          "type": "object",
          "properties": {
            "profile": {
              "const": "omworld.authorization-evidence.v1-draft"
            },
            "object_type": {
              "const": "RelayProfile"
            },
            "id": {
              "type": "string",
              "pattern": "^sha256:[0-9a-f]{64}$"
            },
            "mode": {
              "const": "none"
            }
          },
          "required": [
            "profile",
            "object_type",
            "id",
            "mode"
          ],
          "additionalProperties": false
        },
        {
          "type": "object",
          "properties": {
            "profile": {
              "const": "omworld.authorization-evidence.v1-draft"
            },
            "object_type": {
              "const": "RelayProfile"
            },
            "id": {
              "type": "string",
              "pattern": "^sha256:[0-9a-f]{64}$"
            },
            "mode": {
              "const": "single-trust-path"
            },
            "source_chain": {
              "type": "string",
              "minLength": 1
            },
            "destination_chain": {
              "type": "string",
              "minLength": 1
            },
            "relayer_key": {
              "type": "string",
              "pattern": "^ed25519:[0-9a-f]{64}$"
            },
            "finality_rule_ref": {
              "$ref": "#/$defs/ArtifactRef"
            },
            "freshness_seconds": {
              "type": "integer",
              "minimum": 1
            },
            "receipt_refs": {
              "type": "array",
              "items": {
                "$ref": "#/$defs/ArtifactRef"
              },
              "minItems": 0
            }
          },
          "required": [
            "profile",
            "object_type",
            "id",
            "mode",
            "source_chain",
            "destination_chain",
            "relayer_key",
            "finality_rule_ref",
            "freshness_seconds",
            "receipt_refs"
          ],
          "additionalProperties": false
        }
      ]
    },
    "RestrictionProfile": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "RestrictionProfile"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "extra_confirmation": {
          "enum": [
            "none",
            "affirmative",
            "out_of_band"
          ]
        },
        "not_before": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "expires_at": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "extra_confirmation",
        "not_before",
        "expires_at"
      ],
      "additionalProperties": false
    },
    "CustodyAccessProfile": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "CustodyAccessProfile"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "authorized_reader_keys": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^ed25519:[0-9a-f]{64}$"
          },
          "minItems": 1
        },
        "export": {
          "const": "complete-bytes-manifest-v1"
        },
        "retention_until": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "challenge_ends_at": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "appeal_ends_at": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "authorized_reader_keys",
        "export",
        "retention_until",
        "challenge_ends_at",
        "appeal_ends_at"
      ],
      "additionalProperties": false
    },
    "RegistrySnapshot": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "RegistrySnapshot"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "entry_refs": {
          "type": "array",
          "items": {
            "allOf": [
              {
                "$ref": "#/$defs/Ref"
              },
              {
                "properties": {
                  "object_type": {
                    "const": "ToolEntry"
                  }
                }
              }
            ]
          },
          "minItems": 1
        },
        "registrar_key": {
          "type": "string",
          "pattern": "^ed25519:[0-9a-f]{64}$"
        },
        "snapshot_at": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "signature": {
          "$ref": "#/$defs/Signature"
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "entry_refs",
        "registrar_key",
        "snapshot_at",
        "signature"
      ],
      "additionalProperties": false
    },
    "ToolBehavior": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "ToolBehavior"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "operations": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "operation": {
                "type": "string",
                "minLength": 1
              },
              "classes": {
                "type": "array",
                "items": {
                  "enum": [
                    "read",
                    "write",
                    "destructive",
                    "admin"
                  ]
                },
                "minItems": 1
              },
              "context_mode": {
                "enum": [
                  "pure",
                  "external-state"
                ]
              }
            },
            "required": [
              "operation",
              "classes",
              "context_mode"
            ],
            "additionalProperties": false
          },
          "minItems": 1
        },
        "interface_bytes_ref": {
          "$ref": "#/$defs/ArtifactRef"
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "operations",
        "interface_bytes_ref"
      ],
      "additionalProperties": false
    },
    "Delegation": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "Delegation"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "issuer_root": {
          "type": "string",
          "pattern": "^ed25519:[0-9a-f]{64}$"
        },
        "issuer_key": {
          "type": "string",
          "pattern": "^ed25519:[0-9a-f]{64}$"
        },
        "subject_key": {
          "type": "string",
          "pattern": "^ed25519:[0-9a-f]{64}$"
        },
        "parent_refs": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/ArtifactRef"
          },
          "maxItems": 1
        },
        "action_limits": {
          "$ref": "#/$defs/Limits"
        },
        "issued_at": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "expires_at": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "signature": {
          "$ref": "#/$defs/Signature"
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "issuer_root",
        "issuer_key",
        "subject_key",
        "parent_refs",
        "action_limits",
        "issued_at",
        "expires_at",
        "signature"
      ],
      "additionalProperties": false
    },
    "KeyEvent": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "KeyEvent"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "root": {
          "type": "string",
          "pattern": "^ed25519:[0-9a-f]{64}$"
        },
        "key": {
          "type": "string",
          "pattern": "^ed25519:[0-9a-f]{64}$"
        },
        "state": {
          "enum": [
            "active",
            "rotated",
            "compromised",
            "revoked"
          ]
        },
        "effective_at": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "issuer": {
          "type": "string",
          "pattern": "^ed25519:[0-9a-f]{64}$"
        },
        "signature": {
          "$ref": "#/$defs/Signature"
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "root",
        "key",
        "state",
        "effective_at",
        "issuer",
        "signature"
      ],
      "additionalProperties": false
    },
    "ChannelReceipt": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "ChannelReceipt"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "principal": {
          "type": "string",
          "pattern": "^ed25519:[0-9a-f]{64}$"
        },
        "invocation_ref": {
          "allOf": [
            {
              "$ref": "#/$defs/Ref"
            },
            {
              "properties": {
                "object_type": {
                  "const": "Invocation"
                }
              }
            }
          ]
        },
        "mode": {
          "enum": [
            "affirmative",
            "out_of_band"
          ]
        },
        "channel_id": {
          "type": "string",
          "minLength": 1
        },
        "authority": {
          "type": "string",
          "pattern": "^ed25519:[0-9a-f]{64}$"
        },
        "observed_at": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "signature": {
          "$ref": "#/$defs/Signature"
        },
        "approval_signing_digest": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "principal",
        "invocation_ref",
        "mode",
        "channel_id",
        "authority",
        "observed_at",
        "signature",
        "approval_signing_digest"
      ],
      "additionalProperties": false
    },
    "FinalityRule": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "FinalityRule"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "chain_id": {
          "type": "string",
          "minLength": 1
        },
        "basis": {
          "const": "pinned-relayer-asserted-finality"
        },
        "minimum_confirmations": {
          "type": "integer",
          "minimum": 0
        },
        "maximum_age_seconds": {
          "type": "integer",
          "minimum": 1
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "chain_id",
        "basis",
        "minimum_confirmations",
        "maximum_age_seconds"
      ],
      "additionalProperties": false
    },
    "RelayReceipt": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "RelayReceipt"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "relayer": {
          "type": "string",
          "pattern": "^ed25519:[0-9a-f]{64}$"
        },
        "source_chain": {
          "type": "string",
          "minLength": 1
        },
        "destination_chain": {
          "type": "string",
          "minLength": 1
        },
        "canonical_payload_ref": {
          "$ref": "#/$defs/ArtifactRef"
        },
        "finality_rule_ref": {
          "$ref": "#/$defs/ArtifactRef"
        },
        "observed_at": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "confirmations": {
          "type": "integer",
          "minimum": 0
        },
        "signature": {
          "$ref": "#/$defs/Signature"
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "relayer",
        "source_chain",
        "destination_chain",
        "canonical_payload_ref",
        "finality_rule_ref",
        "observed_at",
        "confirmations",
        "signature"
      ],
      "additionalProperties": false
    },
    "BudgetEvent": {
      "type": "object",
      "properties": {
        "profile": {
          "const": "omworld.authorization-evidence.v1-draft"
        },
        "object_type": {
          "const": "BudgetEvent"
        },
        "id": {
          "type": "string",
          "pattern": "^sha256:[0-9a-f]{64}$"
        },
        "deployment_id": {
          "type": "string",
          "minLength": 1
        },
        "sequence": {
          "type": "integer",
          "minimum": 0
        },
        "previous_event_refs": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/ArtifactRef"
          },
          "maxItems": 1
        },
        "invocation_ref": {
          "allOf": [
            {
              "$ref": "#/$defs/Ref"
            },
            {
              "properties": {
                "object_type": {
                  "const": "Invocation"
                }
              }
            }
          ]
        },
        "acceptance_ref": {
          "allOf": [
            {
              "$ref": "#/$defs/Ref"
            },
            {
              "properties": {
                "object_type": {
                  "const": "Acceptance"
                }
              }
            }
          ]
        },
        "event": {
          "enum": [
            "reserve",
            "consume",
            "release"
          ]
        },
        "amount": {
          "$ref": "#/$defs/Money"
        },
        "observed_at": {
          "type": "string",
          "format": "date-time",
          "pattern": "Z$"
        },
        "authority": {
          "type": "string",
          "pattern": "^ed25519:[0-9a-f]{64}$"
        },
        "signature": {
          "$ref": "#/$defs/Signature"
        }
      },
      "required": [
        "profile",
        "object_type",
        "id",
        "deployment_id",
        "sequence",
        "previous_event_refs",
        "invocation_ref",
        "acceptance_ref",
        "event",
        "amount",
        "observed_at",
        "authority",
        "signature"
      ],
      "additionalProperties": false
    }
  }
}
```
