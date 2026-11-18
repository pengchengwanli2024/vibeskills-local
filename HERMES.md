# Hermes 宿主安装说明

`skills/vibe` 自带安装器，必须用它生成安装回执，否则 `check` 会判失败。

## 安装

```bash
cd skills/vibe
bash install.sh --skills-dir ~/.hermes/skills/software-development
```

前置条件：Python 3.10+（macOS 可用 `python3.13`/`python3.14`）与 PowerShell 7+。
解析器会在受管缓存目录里自建运行时，不改宿主配置。

## 验证

```bash
cd ~/.hermes/skills/software-development/vibe
bash check.sh --skills-dir ~/.hermes/skills/software-development
```

必须带 `--skills-dir`：不带时默认读 `~/.agents/skills/vibe`，会误报
`missing_receipt`，那不是安装失败。

期望：`"ok": true`，`missing_files` 与 `drifted_files` 为空；
`extra_files` 里的 `__pycache__/*.pyc` 是运行时 Bytecode 缓存，不是漂移。

## 更新

```bash
bash update.sh --skills-dir ~/.hermes/skills/software-development
```

同一个受管目录不要混用多个安装源。
