---
name: terminfo-tic-ncurses
description: "「missing or unsuitable terminal: xterm-ghostty」修法——~/.terminfo 必须用系统 /usr/bin/tic 编译，miniforge 的新版 tic 编出的二进制系统 ncurses 读不了"
metadata: 
  node_type: memory
  type: reference
  originSessionId: cf62bce3-25bc-4d53-9ccd-8a7442d3a922
  modified: 2026-08-12T12:23:16.024Z
---

**症状**：远端 tmux/程序报 `missing or unsuitable terminal: xterm-ghostty`（或其他自装 terminfo 条目找不到），但 `~/.terminfo` 里明明有文件。

**原因**：机器上有两套 ncurses——miniforge 环境里的新版和系统 `/usr/lib` 的旧版。miniforge 的新版 `tic` 编出来的 terminfo 二进制格式，系统 ncurses（`/usr/bin/tmux` 链接的那个）读不了。文件在，格式不兼容。

**修法**（2026-08-12 实战验证，xterm-ghostty 已装好）：编译必须显式用系统的 `/usr/bin/tic`：

```
infocmp -x xterm-ghostty | TERMINFO=$HOME/.terminfo /usr/bin/tic -x -
```

（infocmp 在有该终端定义的机器上跑——比如 Mac 本地生成后 ssh 到远端执行编译。）

`~/.terminfo` 在 NFS home 上，装一次全部 16 台机器共享。今后再装任何新终端的 terminfo 都照此办理，别用 PATH 里搜到的 tic。
