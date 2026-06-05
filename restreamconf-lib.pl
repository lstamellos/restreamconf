# restreamconf-lib.pl - helpers for the Virtualmin/Webmin restream module.

BEGIN { push(@INC, '..'); };
use WebminCore;
use Sys::Hostname qw(hostname);

init_config();
our $module_config_directory ||= $config_directory;
our $DEFAULT_INCOMING_PORT = 1935;
our $DEFAULT_INCOMING_HOST = hostname() || 'localhost';

sub restreamconf_config_path {
    return $config{'streams_file'} || "$module_config_directory/streams.conf";
}

sub restreamconf_default_group_id {
    return 'default';
}

sub restreamconf_default_config {
    return {
        incoming_host => $config{'incoming_host'} || $DEFAULT_INCOMING_HOST,
        incoming_port => $DEFAULT_INCOMING_PORT,
        groups => [ { id => restreamconf_default_group_id(), enabled => 1, name => 'Default group' } ],
        streams => [],
    };
}

sub restreamconf_new_id {
    my ($prefix, $index) = @_;
    $prefix ||= 'item';
    $index = 0 if (!defined($index));
    return $prefix . '_' . time() . '_' . int($index);
}

sub restreamconf_escape {
    my ($value) = @_;
    $value = '' if (!defined($value));
    $value =~ s/([^A-Za-z0-9\-_.~])/sprintf('%%%02X', ord($1))/eg;
    return $value;
}

sub restreamconf_unescape {
    my ($value) = @_;
    $value = '' if (!defined($value));
    $value =~ s/%([0-9A-Fa-f]{2})/chr(hex($1))/eg;
    return $value;
}

sub restreamconf_normalize_groups {
    my ($data) = @_;
    $data->{'groups'} ||= [];
    $data->{'streams'} ||= [];

    my %seen;
    my @groups;
    foreach my $group (@{$data->{'groups'}}) {
        my $id = $group->{'id'} || restreamconf_default_group_id();
        next if ($seen{$id});
        push(@groups, {
            id => $id,
            enabled => $group->{'enabled'} ? 1 : 0,
            name => $group->{'name'} || 'Default group',
        });
        $seen{$id} = 1;
    }

    if (!@groups) {
        push(@groups, { id => restreamconf_default_group_id(), enabled => 1, name => 'Default group' });
        $seen{restreamconf_default_group_id()} = 1;
    }

    my $fallback_group = $groups[0]->{'id'};
    foreach my $stream (@{$data->{'streams'}}) {
        my $group_id = $stream->{'group_id'} || $fallback_group;
        if (!$seen{$group_id}) {
            push(@groups, { id => $group_id, enabled => 1, name => 'Group' });
            $seen{$group_id} = 1;
        }
        $stream->{'group_id'} = $group_id;
    }

    $data->{'groups'} = \@groups;
    return $data;
}

sub restreamconf_groups_by_id {
    my ($data) = @_;
    my %groups;
    foreach my $group (@{$data->{'groups'} || []}) {
        $groups{$group->{'id'}} = $group if ($group->{'id'});
    }
    return %groups;
}

sub restreamconf_stream_group {
    my ($data, $stream) = @_;
    my %groups = restreamconf_groups_by_id($data);
    return $groups{$stream->{'group_id'}} || ($data->{'groups'} || [])->[0] || { enabled => 1, name => 'Default group' };
}

sub restreamconf_stream_active {
    my ($data, $stream) = @_;
    my $group = restreamconf_stream_group($data, $stream);
    return ($group->{'enabled'} && $stream->{'enabled'} && $stream->{'url'}) ? 1 : 0;
}


sub restreamconf_read_config {
    my $path = restreamconf_config_path();
    my $data = restreamconf_default_config();
    $data->{'groups'} = [];
    return restreamconf_normalize_groups($data) if (!-r $path);

    open(my $fh, '<', $path) || return restreamconf_normalize_groups($data);
    while (my $line = <$fh>) {
        chomp($line);
        next if ($line =~ /^\s*#/ || $line =~ /^\s*$/);
        if ($line =~ /^incoming_host=(.*)$/) {
            my $host = restreamconf_unescape($1);
            $data->{'incoming_host'} = $host if ($host ne '');
        }
        elsif ($line =~ /^incoming_port=(\d+)$/) {
            $data->{'incoming_port'} = $1;
        }
        elsif ($line =~ /^group=(.*)$/) {
            my @parts = split(/\|/, $1, -1);
            next if (@parts < 3);
            push(@{$data->{'groups'}}, {
                id => restreamconf_unescape($parts[0]),
                enabled => $parts[1] ? 1 : 0,
                name => restreamconf_unescape($parts[2]),
            });
        }
        elsif ($line =~ /^stream=(.*)$/) {
            my @parts = split(/\|/, $1, -1);
            next if (@parts < 6);
            push(@{$data->{'streams'}}, {
                id => restreamconf_unescape($parts[0]),
                enabled => $parts[1] ? 1 : 0,
                name => restreamconf_unescape($parts[2]),
                protocol => lc(restreamconf_unescape($parts[3]) || 'rtmp'),
                url => restreamconf_unescape($parts[4]),
                key => restreamconf_unescape($parts[5]),
                group_id => restreamconf_unescape($parts[6] || ''),
            });
        }
    }
    close($fh);
    return restreamconf_normalize_groups($data);
}

sub restreamconf_write_config {
    my ($data) = @_;
    my $path = restreamconf_config_path();
    my ($dir) = $path =~ /^(.*)\/[^\/]+$/;
    make_dir($dir, 0700) if ($dir && !-d $dir);

    open(my $fh, '>', $path) || &error("Failed to write $path: $!");
    print $fh "# Managed by Webmin/Virtualmin Restream Configuration.\n";
    print $fh "incoming_host=" . restreamconf_escape($data->{'incoming_host'} || $config{'incoming_host'} || $DEFAULT_INCOMING_HOST) . "\n";
    print $fh "incoming_port=" . int($data->{'incoming_port'} || $DEFAULT_INCOMING_PORT) . "\n";
    $data = restreamconf_normalize_groups($data);
    foreach my $group (@{$data->{'groups'} || []}) {
        print $fh join('|',
            'group=' . restreamconf_escape($group->{'id'}),
            $group->{'enabled'} ? 1 : 0,
            restreamconf_escape($group->{'name'}),
        ) . "\n";
    }
    foreach my $stream (@{$data->{'streams'} || []}) {
        print $fh join('|',
            'stream=' . restreamconf_escape($stream->{'id'}),
            $stream->{'enabled'} ? 1 : 0,
            restreamconf_escape($stream->{'name'}),
            restreamconf_escape($stream->{'protocol'} || 'rtmp'),
            restreamconf_escape($stream->{'url'}),
            restreamconf_escape($stream->{'key'}),
            restreamconf_escape($stream->{'group_id'} || restreamconf_default_group_id()),
        ) . "\n";
    }
    close($fh);
    chmod(0600, $path);
}

sub restreamconf_valid_port {
    my ($port) = @_;
    return (defined($port) && $port =~ /^\d+$/ && $port >= 1 && $port <= 65535);
}

sub restreamconf_valid_host {
    my ($host) = @_;
    return (defined($host) && $host =~ /^[A-Za-z0-9_.-]+$/);
}

sub restreamconf_valid_application {
    my ($app) = @_;
    return (defined($app) && $app =~ /^[A-Za-z0-9_-]+$/);
}

sub restreamconf_application {
    my $app = $config{'application'} || 'live';
    return restreamconf_valid_application($app) ? $app : 'live';
}

sub restreamconf_valid_service_name {
    my ($service) = @_;
    return (defined($service) && $service =~ /^[A-Za-z0-9_.@:-]+$/);
}

sub restreamconf_safe_service_name {
    my ($service, $default) = @_;
    return restreamconf_valid_service_name($service) ? $service : $default;
}

sub restreamconf_safe_local_host {
    my $host = $config{'local_rtmp_host'} || '127.0.0.1';
    return ($host =~ /^[A-Za-z0-9_.:-]+$/) ? $host : '127.0.0.1';
}

sub restreamconf_incoming_endpoint {
    my ($data) = @_;
    my $host = $data->{'incoming_host'} || $config{'incoming_host'} || $DEFAULT_INCOMING_HOST;
    my $port = int($data->{'incoming_port'} || $DEFAULT_INCOMING_PORT);
    my $app = restreamconf_application();
    return "rtmp://$host:$port/$app";
}

sub restreamconf_normalize_stream_url {
    my ($url, $key) = @_;
    $url =~ s/^\s+|\s+$//g;
    $key =~ s/^\s+|\s+$//g if (defined($key));
    return $url if (!defined($key) || $key eq '');
    return $url if ($url =~ /\Q$key\E$/);
    $url =~ s/\/$//;
    return "$url/$key";
}

sub restreamconf_parse_rtmp_url {
    my ($url) = @_;
    if ($url !~ m!^(rtmps?)://([^/:/]+)(?::(\d+))?(/.*)?$!i) {
        return undef;
    }
    return {
        protocol => lc($1),
        host => $2,
        port => $3 || (lc($1) eq 'rtmps' ? 443 : 1935),
        path => $4 || '/',
    };
}

sub restreamconf_stream_local_port {
    my ($index) = @_;
    my $base_port = int($config{'local_rtmps_base_port'} || 19350);
    # Migrate older module installs that still have the previous default saved.
    $base_port = 19350 if ($base_port == 31935);
    return $base_port + int($index);
}

sub restreamconf_enabled_rtmps_streams {
    my ($data) = @_;
    my @streams;
    foreach my $stream (@{$data->{'streams'} || []}) {
        next if (!restreamconf_stream_active($data, $stream));
        my $url = restreamconf_normalize_stream_url($stream->{'url'}, $stream->{'key'});
        my $parsed = restreamconf_parse_rtmp_url($url);
        next if (!$parsed || $parsed->{'protocol'} ne 'rtmps');
        push(@streams, [ $stream, $parsed ]);
    }
    return @streams;
}

sub restreamconf_remove_generated_file {
    my ($path) = @_;
    return 0 if (!$path || !-f $path);
    open(my $fh, '<', $path) || return 0;
    my $first = <$fh> || '';
    close($fh);
    return 0 if ($first !~ /^# Managed by Webmin\/Virtualmin Restream Configuration\./);
    unlink($path);
    return 1;
}

sub restreamconf_nginx_listen_directives {
    my ($port) = @_;
    my @directives = ("        listen 0.0.0.0:$port;\n");
    if (!defined($config{'listen_ipv6'}) || $config{'listen_ipv6'} !~ /^(0|no|false)$/i) {
        push(@directives, "        listen [::]:$port ipv6only=on;\n");
    }
    return join('', @directives);
}

sub restreamconf_nginx_conf {
    my ($data) = @_;
    my $app = restreamconf_application();
    my $incoming_port = int($data->{'incoming_port'} || $DEFAULT_INCOMING_PORT);
    my $listen_directives = restreamconf_nginx_listen_directives($incoming_port);
    my $local_host = restreamconf_safe_local_host();
    my $rtmps_index = 0;
    my $conf = "# Managed by Webmin/Virtualmin Restream Configuration.\n" .
               "# Include this file from nginx.conf at top level; it only defines the rtmp context.\n" .
               "rtmp {\n" .
               "    server {\n" .
               $listen_directives .
               "        chunk_size 4096;\n\n" .
               "        application $app {\n" .
               "            live on;\n" .
               "            record off;\n";

    foreach my $stream (@{$data->{'streams'} || []}) {
        next if (!restreamconf_stream_active($data, $stream));
        my $url = restreamconf_normalize_stream_url($stream->{'url'}, $stream->{'key'});
        my $parsed = restreamconf_parse_rtmp_url($url);
        next if (!$parsed);
        my $group = restreamconf_stream_group($data, $stream);
        my $label = ($group->{'name'} ? $group->{'name'} . ' / ' : '') . ($stream->{'name'} || $stream->{'id'} || 'stream');
        $label =~ s/[\r\n#]/ /g;
        if ($parsed->{'protocol'} eq 'rtmps') {
            my $local_port = restreamconf_stream_local_port($rtmps_index++);
            $conf .= "            push rtmp://$local_host:$local_port$parsed->{'path'}; # $label via stunnel4\n";
        }
        else {
            $conf .= "            push $url; # $label\n";
        }
    }

    $conf .= "        }\n" .
             "    }\n" .
             "}\n";
    return $conf;
}

sub restreamconf_stunnel_conf {
    my ($data) = @_;
    my $local_host = restreamconf_safe_local_host();
    my $rtmps_index = 0;
    my @rtmps_streams = restreamconf_enabled_rtmps_streams($data);
    return undef if (!@rtmps_streams);

    my $conf = "# Managed by Webmin/Virtualmin Restream Configuration.\n" .
               "foreground = no\n" .
               "pid = /run/stunnel4/restreamconf.pid\n\n";

    foreach my $entry (@rtmps_streams) {
        my ($stream, $parsed) = @{$entry};
        my $local_port = restreamconf_stream_local_port($rtmps_index++);
        my $service = $stream->{'id'} || "rtmps_$rtmps_index";
        $service =~ s/[^A-Za-z0-9_-]/_/g;
        $conf .= "[$service]\n" .
                 "client = yes\n" .
                 "accept = $local_host:$local_port\n" .
                 "connect = $parsed->{'host'}:$parsed->{'port'}\n" .
                 "sni = $parsed->{'host'}\n" .
                 "verifyChain = no\n\n";
    }
    return $conf;
}


sub restreamconf_stunnel_config_path {
    my $legacy_stunnel_path = '/etc/stunnel/restreamconf.conf';
    my $stunnel_path = $config{'stunnel_conf'} || '/etc/stunnel/conf.d/restreamconf.conf';

    # Older module installs wrote a top-level file under /etc/stunnel.
    # Ubuntu/Debian stunnel4 also starts every top-level *.conf separately,
    # so place the default module snippet under conf.d instead.
    return '/etc/stunnel/conf.d/restreamconf.conf' if ($stunnel_path eq $legacy_stunnel_path);
    return $stunnel_path;
}


sub restreamconf_nginx_main_conf_path {
    return $config{'nginx_main_conf'} || '/etc/nginx/nginx.conf';
}

sub restreamconf_manage_nginx_include {
    return 1 if (!defined($config{'manage_nginx_include'}) || $config{'manage_nginx_include'} eq '');
    return ($config{'manage_nginx_include'} !~ /^(0|no|false)$/i);
}

sub restreamconf_ensure_nginx_include {
    my ($nginx_path) = @_;
    return 0 if (!restreamconf_manage_nginx_include());

    my $main_conf = restreamconf_nginx_main_conf_path();
    return 0 if (!$main_conf || !-f $main_conf || !-r $main_conf || !-w $main_conf);

    open(my $in, '<', $main_conf) || return 0;
    my @lines = <$in>;
    close($in);

    my $include_line = "include $nginx_path;";
    foreach my $line (@lines) {
        return 0 if ($line =~ /^\s*include\s+\Q$nginx_path\E\s*;\s*$/);
    }

    my @updated;
    my $inserted = 0;
    foreach my $line (@lines) {
        if (!$inserted && $line =~ /^\s*http\s*\{/) {
            push(@updated,
                "# Managed by Webmin/Virtualmin Restream Configuration.\n",
                "$include_line\n\n");
            $inserted = 1;
        }
        push(@updated, $line);
    }
    if (!$inserted) {
        push(@updated,
            "\n# Managed by Webmin/Virtualmin Restream Configuration.\n",
            "$include_line\n");
    }

    open(my $out, '>', $main_conf) || return 0;
    print $out @updated;
    close($out);
    return 1;
}

sub restreamconf_write_service_files {
    my ($data) = @_;
    my $nginx_path = $config{'nginx_conf'} || '/etc/nginx/restreamconf/rtmp.conf';
    my $stunnel_path = restreamconf_stunnel_config_path();
    my $legacy_stunnel_path = '/etc/stunnel/restreamconf.conf';

    my ($nginx_dir) = $nginx_path =~ /^(.*)\/[^\/]+$/;
    make_dir($nginx_dir, 0755) if ($nginx_dir && !-d $nginx_dir);

    open(my $nginx, '>', $nginx_path) || &error("Failed to write $nginx_path: $!");
    print $nginx restreamconf_nginx_conf($data);
    close($nginx);
    restreamconf_ensure_nginx_include($nginx_path);

    my $stunnel_conf = restreamconf_stunnel_conf($data);
    if (defined($stunnel_conf)) {
        my ($stunnel_dir) = $stunnel_path =~ /^(.*)\/[^\/]+$/;
        make_dir($stunnel_dir, 0755) if ($stunnel_dir && !-d $stunnel_dir);
        open(my $stunnel, '>', $stunnel_path) || &error("Failed to write $stunnel_path: $!");
        print $stunnel $stunnel_conf;
        close($stunnel);

        if ($stunnel_path ne $legacy_stunnel_path) {
            restreamconf_remove_generated_file($legacy_stunnel_path);
        }
    }
    else {
        restreamconf_remove_generated_file($stunnel_path);
        if ($stunnel_path ne $legacy_stunnel_path) {
            restreamconf_remove_generated_file($legacy_stunnel_path);
        }
    }
}


sub restreamconf_enabled_rtmps_local_ports {
    my ($data) = @_;
    my @ports;
    my $rtmps_index = 0;
    foreach my $entry (restreamconf_enabled_rtmps_streams($data)) {
        push(@ports, restreamconf_stream_local_port($rtmps_index++));
    }
    return @ports;
}

sub restreamconf_listening_socket_inodes_for_port {
    my ($port) = @_;
    my %inodes;
    my $hex_port = uc(sprintf('%04X', $port));

    foreach my $path ('/proc/net/tcp', '/proc/net/tcp6') {
        next if (!-r $path);
        open(my $fh, '<', $path) || next;
        while (my $line = <$fh>) {
            next if ($line !~ /^\s*\d+:/);
            my @fields = split(' ', $line);
            next if (@fields < 10);
            my $local = $fields[1];
            my $state = $fields[3];
            my $inode = $fields[9];
            next if ($state ne '0A' || $local !~ /:$hex_port$/ || $inode !~ /^\d+$/ || $inode == 0);
            $inodes{$inode} = 1;
        }
        close($fh);
    }

    return keys(%inodes);
}

sub restreamconf_pids_for_socket_inodes {
    my (@inodes) = @_;
    my %wanted = map { $_ => 1 } @inodes;
    my %pids;
    return () if (!%wanted);

    opendir(my $proc, '/proc') || return ();
    while (my $pid = readdir($proc)) {
        next if ($pid !~ /^\d+$/);
        my $fd_dir = "/proc/$pid/fd";
        opendir(my $fds, $fd_dir) || next;
        while (my $fd = readdir($fds)) {
            next if ($fd =~ /^\.\.?$/);
            my $target = readlink("$fd_dir/$fd");
            if (defined($target) && $target =~ /^socket:\[(\d+)\]$/ && $wanted{$1}) {
                $pids{$pid} = 1;
                last;
            }
        }
        closedir($fds);
    }
    closedir($proc);
    return keys(%pids);
}

sub restreamconf_listening_pids_for_port {
    my ($port) = @_;
    return () if (!restreamconf_valid_port($port));

    my %pids;
    my $ss = `ss -H -ltnp 'sport = :$port' 2>/dev/null`;
    while ($ss =~ /pid=(\d+)/g) {
        $pids{$1} = 1;
    }

    if (!%pids) {
        my $lsof = `lsof -nP -iTCP:$port -sTCP:LISTEN -t 2>/dev/null`;
        foreach my $line (split(/\n/, $lsof)) {
            $pids{$line} = 1 if ($line =~ /^\d+$/);
        }
    }

    if (!%pids) {
        foreach my $pid (restreamconf_pids_for_socket_inodes(restreamconf_listening_socket_inodes_for_port($port))) {
            $pids{$pid} = 1;
        }
    }

    return keys(%pids);
}

sub restreamconf_release_stunnel_ports {
    my ($data) = @_;
    my %released;

    foreach my $port (restreamconf_enabled_rtmps_local_ports($data)) {
        my @pids = restreamconf_listening_pids_for_port($port);
        next if (!@pids);

        kill('TERM', @pids);
        for (my $i = 0; $i < 10 && restreamconf_listening_pids_for_port($port); $i++) {
            select(undef, undef, undef, 0.2);
        }

        @pids = restreamconf_listening_pids_for_port($port);
        kill('KILL', @pids) if (@pids);
        for (my $i = 0; $i < 10 && restreamconf_listening_pids_for_port($port); $i++) {
            select(undef, undef, undef, 0.2);
        }

        $released{$port} = 1 if (!restreamconf_listening_pids_for_port($port));
    }

    return sort { $a <=> $b } keys(%released);
}

sub restreamconf_apply_services {
    my ($data) = @_;
    restreamconf_write_service_files($data);
    my @messages;
    my $nginx_service = restreamconf_safe_service_name($config{'nginx_service'} || 'nginx', 'nginx');
    my $stunnel_service = restreamconf_safe_service_name($config{'stunnel_service'} || 'stunnel4', 'stunnel4');

    my ($code, $out) = restreamconf_command_output('systemctl', 'restart', $nginx_service);
    push(@messages, "$nginx_service: " . ($code ? "restart failed - $out" : "restarted"));

    if (restreamconf_enabled_rtmps_streams($data)) {
        restreamconf_command_output('systemctl', 'stop', $stunnel_service);
        restreamconf_command_output('systemctl', 'kill', '-s', 'KILL', $stunnel_service);
        my @released_ports = restreamconf_release_stunnel_ports($data);
        ($code, $out) = restreamconf_command_output('systemctl', 'start', $stunnel_service);
        my $result = $code ? "start failed - $out" : "started";
        $result .= "; released stale listeners on ports " . join(', ', @released_ports) if (@released_ports);
        push(@messages, "$stunnel_service: $result");
    }
    else {
        push(@messages, "$stunnel_service: skipped (no enabled RTMPS destinations)");
    }
    return @messages;
}



sub restreamconf_command_output {
    my (@cmd) = @_;
    return (127, 'no command specified') if (!@cmd);

    my $pid = open(my $fh, '-|');
    return (127, "failed to fork for $cmd[0]: $!") if (!defined($pid));
    if ($pid == 0) {
        open(STDERR, '>&', STDOUT);
        exec @cmd;
        print "exec failed for $cmd[0]: $!\n";
        exit 127;
    }

    my $out = do { local $/; <$fh> };
    close($fh);
    my $status = $?;
    my $code = $status == -1 ? 127 : (($status & 127) ? 128 + ($status & 127) : ($status >> 8));
    $out = '' if (!defined($out));
    chomp($out);
    return ($code, $out);
}

sub restreamconf_nginx_include_status {
    my $nginx_path = $config{'nginx_conf'} || '/etc/nginx/restreamconf/rtmp.conf';
    my $main_conf = restreamconf_nginx_main_conf_path();
    return 'main nginx config is not readable' if (!$main_conf || !-r $main_conf);
    open(my $fh, '<', $main_conf) || return "failed to read $main_conf: $!";
    my $content = do { local $/; <$fh> };
    close($fh);
    return ($content =~ /^\s*include\s+\Q$nginx_path\E\s*;\s*$/m) ? 'included' : 'missing include';
}

sub restreamconf_render_diagnostics {
    my ($data) = @_;
    my $nginx_path = $config{'nginx_conf'} || '/etc/nginx/restreamconf/rtmp.conf';
    my $incoming_port = int($data->{'incoming_port'} || $DEFAULT_INCOMING_PORT);
    my @incoming_pids = restreamconf_listening_pids_for_port($incoming_port);
    my @rtmps = restreamconf_enabled_rtmps_streams($data);
    my @ports = restreamconf_enabled_rtmps_local_ports($data);
    my $local_host = restreamconf_safe_local_host();
    my $stunnel_path = restreamconf_stunnel_config_path();
    my ($nginx_test_code, $nginx_test_out) = restreamconf_command_output('nginx', '-t');

    my $html = '<h3>Diagnostics</h3>';
    $html .= '<p>Use this section to locate where stunnel RTMPS forwarding stops: nginx config loading, incoming listener, local RTMP push target generation, stunnel configuration, or stunnel listener ports.</p>';
    $html .= &ui_columns_start([ 'Check', 'Result' ], 100);
    $html .= &ui_columns_row([ 'RTMPS delivery method', 'stunnel4 local TLS tunnels' ]);
    $html .= &ui_columns_row([ 'Generated nginx RTMP config', &html_escape((-r $nginx_path ? "$nginx_path readable" : "$nginx_path missing or unreadable")) ]);
    $html .= &ui_columns_row([ 'Top-level nginx include', &html_escape(restreamconf_nginx_include_status()) ]);
    $html .= &ui_columns_row([ 'nginx -t', &html_escape(($nginx_test_code == 0 ? 'OK' : "FAILED ($nginx_test_code)") . ($nginx_test_out ? ": $nginx_test_out" : '')) ]);
    $html .= &ui_columns_row([ 'Incoming RTMP listener PIDs', &html_escape(@incoming_pids ? join(', ', sort { $a <=> $b } @incoming_pids) : "none found on port $incoming_port") ]);
    $html .= &ui_columns_row([ 'Enabled RTMPS outputs', &html_escape(scalar(@rtmps)) ]);
    $html .= &ui_columns_row([ 'Generated stunnel config', &html_escape((-r $stunnel_path ? "$stunnel_path readable" : "$stunnel_path missing or unreadable")) ]);
    $html .= &ui_columns_row([ 'stunnel local ports', &html_escape(@ports ? join(', ', @ports) : '-') ]);
    $html .= &ui_columns_end();

    if (@rtmps) {
        $html .= '<h4>Generated RTMPS forwarding targets</h4>';
        $html .= &ui_columns_start([ 'Name', 'Generated action' ], 100);
        my $rtmps_index = 0;
        foreach my $entry (@rtmps) {
            my ($stream, $parsed) = @{$entry};
            my $local_port = restreamconf_stream_local_port($rtmps_index++);
            my $action = "nginx pushes to rtmp://$local_host:$local_port$parsed->{'path'}; stunnel connects to $parsed->{'host'}:$parsed->{'port'} with SNI";
            $html .= &ui_columns_row([ &html_escape($stream->{'name'} || $stream->{'id'} || 'stream'), &html_escape($action) ]);
        }
        $html .= &ui_columns_end();
    }

    return $html;
}

sub restreamconf_service_active {
    my ($service) = @_;
    $service = restreamconf_safe_service_name($service, '');
    return 'unknown' if ($service eq '');
    my (undef, $status) = restreamconf_command_output('systemctl', 'is-active', $service);
    return $status || 'unknown';
}

sub restreamconf_render_status_table {
    my ($data) = @_;
    my $incoming_endpoint = restreamconf_incoming_endpoint($data);
    my $html = &ui_columns_start([ 'Type', 'Name', 'Status', 'Endpoint' ], 100);
    $html .= &ui_columns_row([ 'Incoming', 'RTMP ingest', 'public ingest endpoint', &html_escape($incoming_endpoint) ]);
    foreach my $group (@{$data->{'groups'} || []}) {
        my $group_state = $group->{'enabled'} ? 'enabled' : 'disabled';
        $html .= &ui_columns_row([ 'Outgoing group', &html_escape($group->{'name'} || $group->{'id'}), $group_state, '-' ]);
        foreach my $stream (@{$data->{'streams'} || []}) {
            next if (($stream->{'group_id'} || restreamconf_default_group_id()) ne $group->{'id'});
            my $state = restreamconf_stream_active($data, $stream) ? 'active' : ($stream->{'enabled'} ? 'inactive (group disabled)' : 'inactive');
            my $endpoint = restreamconf_normalize_stream_url($stream->{'url'} || '', $stream->{'key'} || '');
            $html .= &ui_columns_row([ 'Outgoing', '&nbsp;&nbsp;' . &html_escape($stream->{'name'} || $stream->{'id'}), $state, &html_escape($endpoint || '-') ]);
        }
    }
    $html .= &ui_columns_end();
    return $html;
}

1;
