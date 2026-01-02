# CLI Reference

EasySweeps provides a set of powerful commands to manage your W&B sweeps. All commands can be accessed via `easysweeps` or the shorter alias `ez`.

## `ez init`

Initialize your project with the required configuration and templates.

::: easysweeps.cli.init
    options:
      show_root_heading: false
      heading_level: 3

---

## `ez sweep`

Create W&B sweeps from your templates and variants.

::: easysweeps.cli.sweep
    options:
      show_root_heading: false
      heading_level: 3

---

## `ez agent`

Launch agents to run experiments for a specific sweep.

::: easysweeps.cli.agent
    options:
      show_root_heading: false
      heading_level: 3

---

## `ez status`

View the current status of all sweeps and running agents.

::: easysweeps.cli.status
    options:
      show_root_heading: false
      heading_level: 3

---

## `ez kill`

Stop running agents or entire sweeps.

::: easysweeps.cli.kill
    options:
      show_root_heading: false
      heading_level: 3
