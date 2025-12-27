import launch
import os

reqs = {
    "webcolors": "webcolors==1.13",
    "colornamer": "colornamer==0.2.3",
    "palettable": "palettable",
    "zhipuai": "zhipuai",
    "qwen-vl-utils": "qwen-vl-utils",
    "google-generativeai": "google-generativeai"
}

def run_pip_safe(install_cmd, desc):
    try:
        launch.run_pip(f"install {install_cmd}", desc)
    except Exception as e:
        print(f"[{desc}] 默认源安装失败，正在尝试切换到清华镜像源...")
        try:
            launch.run_pip(f"install {install_cmd} -i https://pypi.tuna.tsinghua.edu.cn/simple --prefer-binary", f"{desc} (镜像源)")
            print(f"[{desc}] 通过镜像源安装成功！")
        except Exception as e_mirror:
            print(f"Error: 无法安装 {desc}。请检查网络或手动安装。")
            print(e_mirror)

for lib_name, lib_install_cmd in reqs.items():
    if not launch.is_installed(lib_name):
        run_pip_safe(lib_install_cmd, f"sd-forge-next-style requirement: {lib_name}")