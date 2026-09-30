from setuptools import setup
from wheel.bdist_wheel import bdist_wheel

class WindowsX64Wheel(bdist_wheel):
    def finalize_options(self):
        super().finalize_options()
        self.root_is_pure = False
        self.plat_name = "win_amd64"
    def get_tag(self):
        return "py3", "none", "win_amd64"

setup(cmdclass={"bdist_wheel": WindowsX64Wheel})
