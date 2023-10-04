# RCD Nexus Portal

Portal: https://portal.rcd-nexus.org/

WordPress: https://rcd-nexus.org/ 

## Development guide

This project uses Visual Studio Dev Containers to provide easy-to-setup, isolated development environments.

1. Install [VSCode](https://code.visualstudio.com) and [Docker](https://docs.docker.com/engine/install/).
    - For more details, see the official [Dev Containers setup guide](https://code.visualstudio.com/docs/devcontainers/containers#_getting-started).

2. Clone this repository and open it in VSCode.

3. Install the official `Dev Containers` extension for VSCode. The author should be verified as "Microsoft".

4. A prompt may appear to open the current repository in a container. If this does not appear, you can click the green section in the bottom left of the VSCode interface and select "Reopen in container". This will create your isolated development environment.

5. If successful, you can open a VSCode terminal and run `poetry shell` to activate your Python environment and execute `./manage.py` commands, etc.

6. To create a superuser that can access the Admin interface, run `./manage.py createsuperuser`.

### Loading questions and historical data for Capabilities Model

After your environment is built and activated, run `./manage.py loaddata facings legacy_capmodel`. 

To load historical data, first copy the legacy datasets into `data/sensitive/` then run `./manage.py load_nexus_data` from the top of the repository. This may take a couple minutes.

### CILogon integration

The environment variables `CILOGON_CLIENT_ID` and `CILOGON_CLIENT_SECRET` are used to integrate with CILogon.

For example, create or edit `.env` with the content:

```bash
export CILOGON_CLIENT_ID="cilogon:/client_id/<id>"
export CILOGON_CLIENT_SECRET="<secret>"
```

Then run `source .env` in each session.