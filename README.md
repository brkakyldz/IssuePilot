# IssuePilot

An AI agent for investigating GitHub issues and posting evidence-based technical
analysis to the original issue.

## Intended workflow

1. A new issue triggers a GitHub Actions workflow.
2. IssuePilot Core receives the issue and repository context.
3. The LLM directs the investigation using tools to search the repository, read
   source files, and inspect relevant issues and pull requests.
4. The agent posts findings, supporting file references, proposed solutions,
   suggested verification steps, and remaining uncertainties to the issue.

## Design direction

- **Python core:** investigation logic independent of the GitHub Actions runner.
- **GitHub Actions:** run from the repository without a separate server.
- **Bring your own key (BYOK):** users supply their own model API credentials.
- **Bounded autonomy:** explicit limits on research time, tool calls, and cost.
- **Evidence-based output:** distinguish observed facts from hypotheses.
- **Safe investigation:** treat repository and issue content as untrusted input;
  keep credentials out of model context and logs.

## Initial scope

Investigate issues and suggest solutions. Automatic code changes, pull request
creation, and execution of repository code are outside the initial scope.

## Development approach

Build in small, explainable steps. Discuss each component and its tradeoffs
before implementation, then inspect its code and behavior together. Start with
reviewable local output before enabling comments on GitHub.

Define representative issue scenarios and what makes an analysis useful before
building the investigation loop. Select libraries and a model provider after
checking the capabilities needed for the first working example.
