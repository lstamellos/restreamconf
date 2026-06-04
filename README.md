# restreamconf

A Webmin/Virtualmin GPL module for configuring one incoming RTMP ingest and multiple outgoing RTMP/RTMPS restream destinations.

## What the module does

- Provides a Virtualmin/Webmin configuration page for:
  - one incoming RTMP port, configured independently from outgoing destinations;
  - multiple outgoing RTMP or RTMPS stream entries;
  - per-entry enable/disable state;
  - stream URLs with explicit ports when needed;
  - separate stream keys, which are appended to the URL only when provided.
- Generates a module-owned nginx RTMP configuration file without editing existing nginx configuration files.
- Generates a module-owned stunnel4 configuration file for enabled RTMPS destinations.
- Adds Virtualmin integration hooks for:
  - a System Settings link;
  - a dashboard/theme monitoring section showing incoming stream details plus every configured outgoing stream, including inactive entries.

## Generated files

Defaults are stored in `config` and can be changed from Webmin module configuration:

| Setting | Default | Purpose |
| --- | --- | --- |
| `streams_file` | `/etc/webmin/restreamconf/streams.conf` | Module stream database |
| `nginx_conf` | `/etc/nginx/restreamconf/rtmp.conf` | Generated nginx RTMP config |
| `stunnel_conf` | `/etc/stunnel/restreamconf.conf` | Generated stunnel4 client config for RTMPS upstreams |
| `local_rtmps_base_port` | `31935` | First localhost port used for RTMPS tunnel targets |
| `application` | `live` | nginx RTMP application name |

## nginx isolation model

The module writes only its own nginx file and does not modify existing nginx sites or global configuration. To activate the generated RTMP block, include the generated file from the top level of `nginx.conf`, not inside the `http {}` block:

```nginx
include /etc/nginx/restreamconf/rtmp.conf;
```

This keeps normal Virtualmin/nginx web hosting configuration separate from RTMP restreaming. The host must have nginx built with the RTMP module, for example the `libnginx-mod-rtmp` package on Debian/Ubuntu systems that provide it.

## RTMPS handling

nginx RTMP pushes plain RTMP. For RTMPS destinations, this module creates one local stunnel4 client listener per enabled RTMPS output:

1. nginx pushes to `rtmp://127.0.0.1:<local-port>/<remote-path>`;
2. stunnel4 accepts that local connection;
3. stunnel4 connects to the remote RTMPS host and port using TLS.

Inactive RTMPS outputs are saved but do not receive nginx push directives or stunnel4 service entries until re-enabled.

## Installation

From a Webmin modules directory, install this repository as a standard Webmin module or package it as a `.wbm.gz` archive:

```bash
tar czf /tmp/restreamconf.wbm.gz --exclude=.git restreamconf
```

Then install `/tmp/restreamconf.wbm.gz` via **Webmin Configuration → Webmin Modules**.

## Monitoring

The module includes `dashboard.cgi` for a standalone monitoring view and `virtual_feature.pl` `theme_sections` integration for Virtualmin's dashboard/theme area. The monitoring output lists:

- the incoming RTMP ingest endpoint and configured port;
- each active outgoing stream as active;
- each disabled outgoing stream as inactive;
- nginx and stunnel4 service states when available through `systemctl`.
