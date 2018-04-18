# alpha-daemon

Alpha implementation of the SingularityNET daemon

## Getting Started

These instructions are intended to facilitate the development and testing of the alpha SingularityNET Daemon. Users
interested in developing a service for use on the SingularityNet alpha should install the package as
[published](#release) (we have created a simple
[image classification service](https://github.com/singnet/alpha-service-example) as an example).

### Prerequisites

* [Python 3.6.5](https://www.python.org/downloads/release/python-365/)
* [Node 8+ w/npm](https://nodejs.org/en/download/)

### Installing

* Clone the git repository
```bash
$ git clone git@github.com:singnet/alpha-daemon.git
$ cd alpha-daemon
```

* Install development/test blockchain dependencies
```bash
$ ./scripts/blockchain install-dev
```

* Install the package in development/editable mode
```bash
$ pip install -e .
```

### Testing

A simple test script has been setup that does the following
1. Runs a [ganache-cli](https://github.com/trufflesuite/ganache-cli) test RPC with a predetermined mnemonic for account
generation
2. Runs an instance of snetd
3. Deploys the required network singleton contracts (SingularityNetToken, AgentFactory, Registry) and
creates an Agent contract instance at a predetermined address
4. Creates and funds a Job contract instance at a predetermined address
5. Calls the RPC passthrough on the daemon using the predetermined job address and job signature

* Invoke the test script
```bash
$ ./scripts/test
```

## Release

This project is published to [PyPI](https://pypi.org/project/snetd-alpha/).

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the
[tags on this repository](https://github.com/singnet/alpha-daemon/tags). 

## License

This project is licensed under the MIT License - see the
[LICENSE](https://github.com/singnet/alpha-daemon/blob/master/LICENSE) file for details.
