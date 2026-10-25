from setuptools import setup, find_packages

version = "0.0.1.dev0"
name = "slapos.test.mosquitto"

with open("README.md") as f:
  long_description = f.read()

setup(
    name=name,
    version=version,
    description="Test for SlapOS Mosquitto",
    long_description=long_description,
    long_description_content_type="text/markdown",
    maintainer="Nexedi",
    maintainer_email="info@nexedi.com",
    url="https://lab.nexedi.com/nexedi/slapos",
    packages=find_packages(),
    install_requires=[
        "slapos.core",
        "slapos.libnetworkcache",
        "erp5.util",
        "requests",
	"paho-mqtt",
    ],
    zip_safe=True,
    test_suite="test",
)
