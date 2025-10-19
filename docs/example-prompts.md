# Example Prompts for Agents to Develop Workflows

This document provides example prompts that can be used to guide AI agents in developing Temporal workflows.

## Table of Contents

- [Text-based Prompt](#text-based-prompt)
- [Multi-modal Prompt](#multi-modal-prompt)
- [Usage Guidelines](#usage-guidelines)

## Text-based Prompt

```text
Implement an order Workflow with the following steps:

1. check fraud
1. prepare shipment
1. charge customer
1. ship order
```

[![Order Workflow with Cursor](https://img.youtube.com/vi/ePbdiPNsgv4/maxresdefault.jpg)](https://youtu.be/ePbdiPNsgv4)
*Video 1: generate order Workflow using Cursor*

## Multi-modal Prompt

```text
# attach-your-workflow-diagram-as-context
Analyze the provided diagram and convert it into a Temporal Workflow Definition using the Python SDK. You MUST adhere to the given implementation standards defined in AGENTS.md
```

[![Employee Anniversary Workflow with Warp Code](https://img.youtube.com/vi/pgRWSEM7bn4/maxresdefault.jpg)](https://youtu.be/pgRWSEM7bn4)
*Video 2: generate employee anniversary Workflow using Warp Code*

## Usage Guidelines

When using these prompts:

1. **Start Simple**: Begin with simple workflows before iterating on more complex patterns
1. **Follow Project Patterns**: Use the existing project structure and conventions
1. **Test Thoroughly**: Implement comprehensive tests as outlined in `testing.md`
