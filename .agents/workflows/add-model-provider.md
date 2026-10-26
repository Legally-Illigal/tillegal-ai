# Add Model Provider Workflow

## Purpose

Integrate a new LLM provider through the shared model-calling layer while preserving a consistent interface for the rest of the AI Service.

## When to Use

Use this workflow when adding support for a new provider, model API, or provider-specific capability.

## Inputs

- Provider documentation and supported API behavior
- Existing Model Gateway and LiteLLM integration
- Current configuration and secret-management conventions
- Requirements for the models or capabilities being added
- Existing provider tests and observability conventions

## Procedure

### 1. Inspect the Existing Integration

1. Locate the shared Model Gateway and current LiteLLM integration.
2. Inspect model selection, request parameters, response normalization, and error handling.
3. Identify existing abstractions and extension points.
4. Check the installed LiteLLM version and its supported provider configuration.
5. Identify which requirements can be met through existing capabilities.

Do not create a second model-calling abstraction if the existing gateway can support the provider.

### 2. Verify Provider Capabilities

Consult the provider's official documentation and determine:

- Supported model identifiers
- Authentication mechanism
- Required configuration fields
- Supported chat or generation interfaces
- Structured-output or tool-calling support, if needed
- Streaming behavior, if required
- Timeout and error behavior
- Token usage and cost metadata availability
- Rate limits and relevant operational constraints

Distinguish documented capabilities from behavior that has not been verified.

### 3. Design the Integration

Define:

- Provider configuration and model identifier format
- Required environment variables or secret references
- How the provider is selected
- How requests and responses pass through the existing gateway
- How errors are normalized
- How unsupported capabilities are handled
- How timeouts, retries, and fallback are bounded

Do not assume all providers support the same parameters or output formats.

### 4. Implement Configuration

1. Add configuration using existing project conventions.
2. Validate required fields during startup or before invocation, as appropriate.
3. Keep credentials outside source code and version control.
4. Document safe local-development configuration.
5. Do not log credentials or full authentication headers.

Avoid hard-coding a specific developer's model selection into shared defaults.

### 5. Implement Provider Support

1. Register or configure the provider through LiteLLM and the Model Gateway.
2. Normalize responses to the existing internal contract.
3. Preserve available token usage, latency, and cost metadata.
4. Map provider errors into the project's established error categories where appropriate.
5. Handle unsupported features explicitly.
6. Keep provider-specific behavior encapsulated behind the gateway.

Do not expose provider-specific response structures throughout the application unless the approved architecture explicitly requires it.

### 6. Implement Reliability Behavior

Check and document:

- Request timeout handling
- Retry eligibility and maximum attempts
- Rate-limit handling
- Provider unavailability
- Fallback eligibility and selection
- Malformed or incomplete responses
- Cancellation and resource cleanup, where applicable

Retries must be bounded and should not repeat non-retryable failures. Fallback must not silently change required output guarantees or hide persistent provider errors.

### 7. Add Tests

Include appropriate tests for:

- Valid configuration
- Missing or invalid configuration
- Request construction
- Response normalization
- Token usage metadata
- Error mapping
- Timeout and retry behavior
- Fallback behavior, if implemented

Use mocks for unit tests. Run live provider smoke tests only when credentials, connectivity, and authorization are available. Never claim a live test passed if it was not executed.

### 8. Update Documentation and Observability

Document:

- Provider setup and required configuration
- Supported capabilities and limitations
- Model selection conventions
- Troubleshooting guidance
- Relevant metrics and error categories

Track available latency, token usage, and cost information consistently with existing observability conventions. Do not fabricate cost values when the provider does not supply sufficient information.

### 9. Verify Backward Compatibility

Run existing Model Gateway tests and relevant AI workflow regression tests.

Confirm that adding the provider does not alter the behavior of existing provider configurations.

## Guardrails

- Do not bypass the shared Model Gateway without an approved architectural reason.
- Do not commit secrets or expose them in logs.
- Do not assume provider capabilities without verification.
- Do not introduce unbounded retries or silent fallback behavior.
- Do not make all application modules depend on provider-specific SDKs.
- Do not report unsupported cost or token metadata as exact measurements.

## Definition of Done

- [ ] Provider capabilities are documented and verified against available evidence.
- [ ] Configuration follows existing conventions.
- [ ] Integration uses the established Model Gateway.
- [ ] Responses and errors follow the internal contract.
- [ ] Retry, timeout, and fallback behavior are bounded.
- [ ] Unit tests and relevant regression tests pass, or limitations are reported.
- [ ] Documentation and observability are updated.
- [ ] Existing provider behavior remains compatible.