# LiteLLM Integration Skill
---
name: litellm-integration
description: Integrate and maintain LLM providers through the approved Model Gateway using LiteLLM where supported by the project.
---

## Purpose

Provide a consistent process for integrating model providers without coupling application agents to provider-specific SDKs.

LiteLLM is the intended provider-integration mechanism for Tillegal AI Service, subject to the approved architecture and installed version.

## When to Use

- Adding a model provider.
- Adding or changing model configuration.
- Implementing normalized model responses.
- Handling provider errors and timeouts.
- Adding usage and cost metadata.
- Testing fallback behavior.
- Updating provider-specific documentation.

## Procedure

### Step 1: Inspect the Existing Gateway

Review:

- Gateway interfaces and implementation.
- Existing provider adapters.
- Configuration and secret-loading mechanisms.
- Normalized response and error contracts.
- Dependency versions.
- Existing tests and observability hooks.

Extend the existing abstraction rather than creating a competing model-calling path.

### Step 2: Verify Provider Capabilities

Check the relevant LiteLLM version and provider documentation.

Verify only the capabilities needed by the task, such as:

- Supported model identifiers.
- Authentication requirements.
- Supported request parameters.
- Structured-output capabilities.
- Streaming behavior, if required.
- Timeout and retry behavior.
- Usage metadata availability.
- Provider-specific errors and limitations.

Do not assume all providers support identical features.

### Step 3: Define Configuration

Determine the necessary configuration fields and defaults.

Where appropriate, separate:

- Provider and model selection.
- Credentials.
- Endpoint configuration.
- Request parameters.
- Timeout settings.
- Retry policy.
- Fallback configuration.

Keep credentials outside source code. Validate required settings before using the provider.

Do not introduce configuration fields that the implementation does not consume.

### Step 4: Implement the Integration

- Route calls through the shared Model Gateway.
- Use the approved LiteLLM interface.
- Normalize responses according to the gateway contract.
- Translate provider failures into the project's established error model.
- Preserve useful diagnostic context without exposing secrets.
- Apply bounded timeouts and retries.
- Make fallback behavior explicit when configured.

Do not expose raw provider response objects throughout the application when a stable normalized contract is required.

### Step 5: Handle Usage and Cost

Record token usage, latency, and cost only when supported by actual execution metadata or a documented calculation.

- Preserve the distinction between reported and estimated cost.
- Handle missing usage information explicitly.
- Do not infer exact usage from response length.
- Avoid logging sensitive prompts and responses unnecessarily.

### Step 6: Test the Integration

Test successful responses, provider failures, malformed responses, timeout behavior, retry limits, missing usage metadata, and configuration errors.

Use mocked responses for ordinary unit tests.

Run live-provider tests only when explicitly configured and appropriate. Avoid unnecessary charges and sensitive-data exposure.

### Step 7: Document and Review

Document the provider configuration, limitations, required credentials, error behavior, and supported capabilities.

Update related gateway tests and documentation.

## Guardrails

- Do not bypass the Model Gateway.
- Do not hardcode credentials or endpoints.
- Do not silently change the gateway's public contract.
- Do not assume fallback models are interchangeable in capability or quality.
- Do not route sensitive content to an unapproved provider.
- Do not claim a provider supports a feature without verification.

## Expected Output

A provider integration or gateway extension, relevant tests, configuration documentation, and a clear description of verified capabilities and limitations.

## Completion Checklist

- [ ] Existing gateway contracts were inspected.
- [ ] Provider capabilities were verified.
- [ ] Configuration and credentials are handled safely.
- [ ] Responses and errors follow the approved contract.
- [ ] Retry and fallback behavior are bounded.
- [ ] Usage and cost metadata are represented accurately.
- [ ] Tests and documentation are updated.
