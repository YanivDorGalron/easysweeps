# Key Concepts

EasySweeps is built on a few core principles that simplify the management of large-scale experiment sweeps.

## Templates & Variants

The most powerful feature of EasySweeps is the separation of **Hyperparameter Templates** from **Configuration Variants**.

### The Problem
When running sweeps across different datasets (e.g., MNIST and CIFAR-10), you often want to use the same hyperparameter search space (e.g., Grid Search on Learning Rate). Traditionally, this requires:
1. Creating two separate W&B sweep files.
2. Manually duplicating the hyperparameter logic in each.
3. Keeping them in sync when you change a range.

### The EasySweeps Solution
You define **one** template and **one** variants file.

1. **Template**: A standard W&B YAML where some values are placeholders (e.g., `dataset: {dataset}`).
2. **Variants**: A simple mapping of placeholders to list of values.

EasySweeps automatically generates and launches isolated sweeps for every combination, ensuring clean data separation while maintaining a DRY (Don't Repeat Yourself) configuration.

## Systemd Scope Agents

Unlike standard background processes, EasySweeps launches agents inside **systemd scope units**.

- **Isolation**: Each agent group is tracked by the system manager.
- **Reliability**: If your terminal closes, the agents keep running.
- **Easy Cleanup**: The `ez kill` command uses these scopes to safely and completely terminate all processes associated with an agent, including child processes, preventing "zombie" training runs on your GPUs.

## GPU Management

EasySweeps treats GPUs as first-class citizens. By providing a `--gpu-list`, the tool automatically handles `CUDA_VISIBLE_DEVICES` for you, ensuring that two agents never fight over the same hardware unless you explicitly want them to.
