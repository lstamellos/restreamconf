# restreamconf

A Webmin/Virtualmin GPL module for configuring one incoming RTMP ingest and multiple outgoing RTMP/RTMPS restream destinations.

## What the module does

- Provides a Virtualmin/Webmin configuration page for:
  - one public incoming RTMP hostname and one listening port, configured independently from outgoing destinations;
  - multiple outgoing RTMP or RTMPS stream entries;
  - outgoing stream groups that can be enabled or disabled together;
  - per-entry enable/disable state within each group;
  - stream URLs with explicit ports when needed;
  - separate stream keys, which are appended to the URL only when provided.
- Generates a module-owned nginx RTMP configuration file without editing existing nginx configuration files.
- Forwards enabled RTMPS destinations through module-owned stunnel4 TLS tunnels.
- Adds Virtualmin integration hooks for:
  - a System Settings link;
  - a dashboard/theme monitoring section showing incoming stream details plus every configured outgoing stream, including inactive entries.

## Generated files

Defaults are stored in `config` and can be changed from Webmin module configuration:

| Setting | Default | Purpose |
| --- | --- | --- |
| `streams_file` | `/etc/webmin/restreamconf/streams.conf` | Module stream database |
| `nginx_conf` | `/etc/nginx/restreamconf/rtmp.conf` | Generated nginx RTMP config |
| `nginx_main_conf` | `/etc/nginx/nginx.conf` | Main nginx config where the module installs the RTMP include |
| `manage_nginx_include` | `1` | Automatically include the generated RTMP config from the main nginx config |
| `incoming_host` | system hostname | Public hostname shown in the incoming RTMP ingest URL for OBS or other encoders |
| `listen_ipv6` | `1` | Also generate an IPv6 RTMP listener so hostnames with AAAA records work from OBS |
| `stunnel_conf` | `/etc/stunnel/conf.d/restreamconf.conf` | Generated stunnel4 client config for RTMPS upstreams |
| `local_rtmps_base_port` | `19350` | First localhost port used for RTMPS tunnel targets; legacy saved value `31935` is treated as `19350` |
| `application` | `live` | nginx RTMP application name |

## nginx isolation model

The module writes its RTMP server block to its own nginx file and, by default, installs a top-level include for that file in `nginx.conf` before the `http {}` block. The include must be top-level because the nginx RTMP module does not run from inside the HTTP context:

```nginx
include /etc/nginx/restreamconf/rtmp.conf;

http {
    ...
}
```

This keeps normal Virtualmin/nginx web hosting configuration separate from RTMP restreaming while still ensuring nginx actually loads the RTMP listener. The host must have nginx built with the RTMP module, for example the `libnginx-mod-rtmp` package on Debian/Ubuntu systems that provide it.

The generated RTMP server listens on the configured port on IPv4 (`0.0.0.0`) and, by default, IPv6 (`[::]`), while `incoming_host` is the public hostname shown in monitoring and encoder settings. Keeping those separate avoids binding nginx to a DNS name that may resolve to the wrong address family or a non-local address, and the IPv6 listener prevents OBS from getting `ECONNREFUSED` when the hostname resolves to an AAAA record first.

## RTMPS handling

nginx RTMP pushes plain RTMP directly. For RTMPS destinations, this module creates one local stunnel4 client listener per enabled RTMPS output. nginx pushes the incoming stream to `rtmp://127.0.0.1:<local-port>/<remote-path>`, preserving the remote RTMPS path and stream key. stunnel4 accepts that local RTMP connection and connects to the remote RTMPS host using TLS with SNI.

When applying enabled RTMPS outputs, the module stops `stunnel4`, releases any stale listeners still bound to the module-owned local tunnel ports, and then starts `stunnel4`; this avoids `Address already in use` failures from orphaned stunnel processes. Inactive RTMPS outputs, including outputs inside disabled groups, are saved but do not receive nginx push directives or stunnel4 service entries until both their group and their individual row are re-enabled. When no enabled RTMPS outputs exist, the module removes its generated stunnel4 file and skips restarting `stunnel4` so Ubuntu/Debian stunnel does not try to start an empty configuration in inetd mode.

On Ubuntu/Debian, the default stunnel4 package reads snippets from `/etc/stunnel/conf.d` through `/etc/stunnel/stunnel.conf`. The module therefore writes its generated snippet to `/etc/stunnel/conf.d/restreamconf.conf` and removes the older module-owned `/etc/stunnel/restreamconf.conf` file when it can identify the managed header.

## Installation

From a Webmin modules directory, install this repository as a standard Webmin module or package it as a `.wbm.gz` archive:

```bash
tar czf /tmp/restreamconf.wbm.gz --exclude=.git restreamconf
```

Then install `/tmp/restreamconf.wbm.gz` via **Webmin Configuration → Webmin Modules**.

## Monitoring

The module includes `dashboard.cgi` for a standalone monitoring view and `virtual_feature.pl` `theme_sections` integration for Virtualmin's dashboard/theme area. The dashboard diagnostics section checks whether nginx loads the generated RTMP config, whether the incoming port has listener PIDs, what stunnel4 RTMPS forwarding action is generated, and which local tunnel ports are used. The monitoring output lists:

- the incoming RTMP ingest endpoint with the configured hostname, port, and application path;
- each outgoing stream group as enabled or disabled;
- each active outgoing stream as active;
- each individually disabled or group-disabled outgoing stream as inactive;
- nginx and stunnel4 service states when available through `systemctl`.
