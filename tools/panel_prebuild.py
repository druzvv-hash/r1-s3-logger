"""PlatformIO hook: regenerate embedded assets before each build."""
Import("env")
import runpy
runpy.run_path(env.subst("$PROJECT_DIR")+"/tools/build_panel.py")["build"]()
