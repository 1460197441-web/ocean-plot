# PyPI 首次发布：只需一次账号授权

当前尚未发布 PyPI。GitHub Release 的 wheel 可以直接安装，发布到 PyPI 后才可使用 `pip install ocean-plot`。

## 需要仓库主人完成

1. 在 [PyPI 注册](https://pypi.org/account/register/) 账号，验证自己的邮箱，并按页面要求启用二次验证。密码、恢复码和验证码留在自己设备，不发送到聊天。
2. 登录后打开 [Publishing](https://pypi.org/manage/account/publishing/)，添加 **pending publisher / GitHub**，填写：

| 字段 | 填入内容 |
| --- | --- |
| PyPI project name | `ocean-plot` |
| Owner | `1460197441-web` |
| Repository name | `ocean-plot` |
| Workflow name / filename | `publish.yml` |
| Environment name | `pypi` |

这里的 workflow 只填文件名，不填 `.github/workflows/`，也不填界面标题 `publish-pypi`。Pending publisher 不预留项目名；若 PyPI 提示名称冲突，先停止，核实名称。

## 授权完成后

在 [GitHub 发布工作流](https://github.com/1460197441-web/ocean-plot/actions/workflows/publish.yml) 选择 Run workflow：分支 `main`、tag `v0.1.0`、publish 勾选。也可告知代理授权已完成，由代理触发和验收。工作流先检查tag与版本一致，运行测试、构建和twine check，随后用短期OIDC凭据发布，不需要长期token。

默认不勾 publish 时只做构建验收，不会上传。不要对已经发布的同一版本反复上传；PyPI 不允许覆盖版本文件。

成功标准：工作流 publish job 成功、[PyPI 项目页](https://pypi.org/project/ocean-plot/)出现正确版本，并在新环境中验证安装与 demo。随后才把 README 改成 PyPI 安装命令。

官方说明：[创建 pending publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/) · [OIDC 发布工作流](https://docs.pypi.org/trusted-publishers/using-a-publisher/)。
