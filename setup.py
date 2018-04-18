from setuptools import setup

setup(
    name='snetd-alpha',
    version='1.0.0',
    packages=['snetd_alpha'],
    scripts=['bin/snetd'],
    url='https://github.com/singnet/alpha-daemon',
    license='MIT',
    author='SingularityNET',
    author_email='info@singularitynet.io',
    description='SingularityNET Alpha Daemon',
    install_requires=[
        'aiohttp',
        'aiohttp_cors',
        'jsonrpcserver',
        'jsonrpcclient',
        'web3',
        'mnemonic',
        'bip32utils',
        'ecdsa'
    ],
    include_package_data=True
)
