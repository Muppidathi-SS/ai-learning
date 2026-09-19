# Tool Registration Git Diff

Requirement 1: Hand back a 3-line git diff of the tool registration alone.

```diff
 AVAILABLE_TOOLS = {
     "search_docs": search_docs,
     "get_openapi_spec": get_openapi_spec,
+    "check_deprecation": check_deprecation,
 }
```

### Tool Descriptions (Zero Overlap)
1. **`search_docs`**: Search prose documentation, developer guides, and markdown code examples for tutorials, concepts, and usage patterns.
2. **`get_openapi_spec`**: Retrieve OpenAPI schema specification details including HTTP method, path, input parameters, data types, and status responses.
3. **`check_deprecation`**: Query migration changelog and deprecation registry to check if an API symbol or endpoint has been deprecated, and retrieve replacement names.

### Enum Parameter
Version parameter is enforced via `ApiVersion(str, Enum)` with members `V1 = "v1"`, `V2 = "v2"`, and `V3 = "v3"`, avoiding raw string comparisons.
