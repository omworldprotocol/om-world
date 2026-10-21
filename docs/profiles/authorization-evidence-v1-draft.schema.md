# Authorization/evidence v1-draft — structural JSON Schema

Specification material, CC-BY-4.0, under the repository documentation scope. The fenced JSON is the complete machine-readable schema; it can be extracted without editing. This is not a semantic verifier.

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
          "type": "string",
          "minLength": 1
        },
        "key_ref": {
          "$ref": "#/$defs/ArtifactRef"
        },
        "value": {
          "type": "string",
          "minLength": 1
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
          "minLength": 1
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
          "minLength": 1
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
          "minLength": 1
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
          "minLength": 1
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
          "minLength": 1
        },
        "registrar": {
          "type": "string",
          "minLength": 1
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
          "minLength": 1
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
          "minLength": 1
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
          "minLength": 1
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
          "minItems": 0
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
        "exported_evidence_refs"
      ],
      "additionalProperties": false
    }
  }
}
```
