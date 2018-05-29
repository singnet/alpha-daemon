from setuptools import setup

setup(
    name='snetd-alpha',
    version='0.1.0',
    packages=['snetd_alpha'],
    scripts=['bin/snetd'],
    url='https://github.com/singnet/alpha-daemon',
    license='MIT',
    author='SingularityNET',
    author_email='info@singularitynet.io',
    description='SingularityNET Alpha Daemon',
    install_requires=[
        'aiohttp==3.2.1',
        'aiohttp_cors==0.7.0',
        'jsonrpcserver==3.5.4',
        'jsonrpcclient==2.5.2',
        'web3==4.2.1',
        'mnemonic==0.18',
        'bip32utils==0.3.post3',
        'ecdsa==0.13'
    ],
    include_package_data=True
)
