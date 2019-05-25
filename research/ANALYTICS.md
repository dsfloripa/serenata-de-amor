# Analytics tools guide

The pourpose of this guide is to share ideas on how to use open source data analytics tools to explore and get insights from the sources of data of the project.

## Metabase

[Metabase](https://metabase.com) is an open source BI (Business Intelligence) tool. The idea is to connect a source of data (e.g. jarbas postgresql database), ask questions ([using metabase question builder or sql queries](https://metabase.com/docs/latest/users-guide/04-asking-questions.html)), get the answers to build dashboards ([visualize with numbers, tables and charts](https://metabase.com/docs/latest/users-guide/05-visualizing-results.html)) and publish the results.

### Instructions to run locally

1. Install Metabase using one of the options available [here](https://metabase.com/start).

   - We recommend the docker setup with only one command: `docker run -d -p 3000:3000 --name metabase metabase/metabase`

2. Access [localhost:3000](http://localhost:3000) and Connect Metabase with the data source you want to analyse.

   - Connecting with jarbas postgresql database ([running on a docker](../jarbas/README.md)):
     - use the database credentials from `../contrib/.env.sample`
     - use docker internal host: `host.docker.internal`
