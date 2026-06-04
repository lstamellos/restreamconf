# restreamconf-lib.pl - helpers for the Virtualmin/Webmin restream module.

BEGIN { push(@INC, '..'); };
use WebminCore;

init_config();
our $module_config_directory ||= $config_directory;
our $DEFAULT_INCOMING_PORT = 1935;

sub restreamconf_config_path {
    return $config{'streams_file'} || "$module_config_directory/streams.conf";
}

sub restreamconf_default_config {
    return {
        incoming_port => $DEFAULT_INCOMING_PORT,
        streams => [],
    };
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

sub restreamconf_read_config {
    my $path = restreamconf_config_path();
    my $data = restreamconf_default_config();
    return $data if (!-r $path);

    open(my $fh, '<', $path) || return $data;
    while (my $line = <$fh>) {
        chomp($line);
        next if ($line =~ /^\s*#/ || $line =~ /^\s*$/);
        if ($line =~ /^incoming_port=(\d+)$/) {
            $data->{'incoming_port'} = $1;
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
            });
        }
    }
    close($fh);
    return $data;
}

sub restreamconf_write_config {
    my ($data) = @_;
    my $path = restreamconf_config_path();
    my ($dir) = $path =~ /^(.*)\/[^\/]+$/;
    make_dir($dir, 0700) if ($dir && !-d $dir);

    open(my $fh, '>', $path) || &error("Failed to write $path: $!");
    print $fh "# Managed by Webmin/Virtualmin Restream Configuration.\n";
    print $fh "incoming_port=" . int($data->{'incoming_port'} || $DEFAULT_INCOMING_PORT) . "\n";
    foreach my $stream (@{$data->{'streams'} || []}) {
        print $fh join('|',
            'stream=' . restreamconf_escape($stream->{'id'}),
            $stream->{'enabled'} ? 1 : 0,
            restreamconf_escape($stream->{'name'}),
            restreamconf_escape($stream->{'protocol'} || 'rtmp'),
            restreamconf_escape($stream->{'url'}),
            restreamconf_escape($stream->{'key'}),
        ) . "\n";
    }
    close($fh);
    chmod(0600, $path);
}

sub restreamconf_valid_port {
    my ($port) = @_;
    return ($port =~ /^\d+$/ && $port >= 1 && $port <= 65535);
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
    return int($config{'local_rtmps_base_port'} || 31935) + int($index);
}

sub restreamconf_enabled_streams {
    my ($data) = @_;
    return grep { $_->{'enabled'} && $_->{'url'} } @{$data->{'streams'} || []};
}

sub restreamconf_nginx_conf {
    my ($data) = @_;
    my $app = $config{'application'} || 'live';
    my $incoming_port = int($data->{'incoming_port'} || $DEFAULT_INCOMING_PORT);
    my $local_host = $config{'local_rtmp_host'} || '127.0.0.1';
    my $rtmps_index = 0;
    my $conf = "# Managed by Webmin/Virtualmin Restream Configuration.\n" .
               "# Include this file from nginx.conf at top level; it only defines the rtmp context.\n" .
               "rtmp {\n" .
               "    server {\n" .
               "        listen $incoming_port;\n" .
               "        chunk_size 4096;\n\n" .
               "        application $app {\n" .
               "            live on;\n" .
               "            record off;\n";

    foreach my $stream (@{$data->{'streams'} || []}) {
        next if (!$stream->{'enabled'} || !$stream->{'url'});
        my $url = restreamconf_normalize_stream_url($stream->{'url'}, $stream->{'key'});
        my $parsed = restreamconf_parse_rtmp_url($url);
        next if (!$parsed);
        my $label = $stream->{'name'} || $stream->{'id'} || 'stream';
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
    my $local_host = $config{'local_rtmp_host'} || '127.0.0.1';
    my $rtmps_index = 0;
    my $conf = "# Managed by Webmin/Virtualmin Restream Configuration.\n" .
               "foreground = no\n" .
               "pid = /run/stunnel4/restreamconf.pid\n\n";

    foreach my $stream (@{$data->{'streams'} || []}) {
        next if (!$stream->{'enabled'} || !$stream->{'url'});
        my $url = restreamconf_normalize_stream_url($stream->{'url'}, $stream->{'key'});
        my $parsed = restreamconf_parse_rtmp_url($url);
        next if (!$parsed || $parsed->{'protocol'} ne 'rtmps');
        my $local_port = restreamconf_stream_local_port($rtmps_index++);
        my $service = $stream->{'id'} || "rtmps_$rtmps_index";
        $service =~ s/[^A-Za-z0-9_-]/_/g;
        $conf .= "[$service]\n" .
                 "client = yes\n" .
                 "accept = $local_host:$local_port\n" .
                 "connect = $parsed->{'host'}:$parsed->{'port'}\n" .
                 "verifyChain = no\n\n";
    }
    return $conf;
}

sub restreamconf_write_service_files {
    my ($data) = @_;
    my $nginx_path = $config{'nginx_conf'} || '/etc/nginx/restreamconf/rtmp.conf';
    my $stunnel_path = $config{'stunnel_conf'} || '/etc/stunnel/restreamconf.conf';

    foreach my $path ($nginx_path, $stunnel_path) {
        my ($dir) = $path =~ /^(.*)\/[^\/]+$/;
        make_dir($dir, 0755) if ($dir && !-d $dir);
    }

    open(my $nginx, '>', $nginx_path) || &error("Failed to write $nginx_path: $!");
    print $nginx restreamconf_nginx_conf($data);
    close($nginx);

    open(my $stunnel, '>', $stunnel_path) || &error("Failed to write $stunnel_path: $!");
    print $stunnel restreamconf_stunnel_conf($data);
    close($stunnel);
}

sub restreamconf_restart_command {
    my ($service) = @_;
    return "systemctl restart " . quotemeta($service);
}

sub restreamconf_apply_services {
    restreamconf_write_service_files(@_);
    my @messages;
    foreach my $service ($config{'nginx_service'} || 'nginx', $config{'stunnel_service'} || 'stunnel4') {
        my $cmd = "systemctl restart " . quotemeta($service) . " 2>&1";
        my $out = `$cmd`;
        push(@messages, "$service: " . ($? ? "restart failed - $out" : "restarted"));
    }
    return @messages;
}

sub restreamconf_service_active {
    my ($service) = @_;
    my $status = `systemctl is-active $service 2>/dev/null`;
    chomp($status);
    return $status || 'unknown';
}

sub restreamconf_render_status_table {
    my ($data) = @_;
    my $incoming_port = int($data->{'incoming_port'} || $DEFAULT_INCOMING_PORT);
    my $html = &ui_columns_start([ 'Type', 'Name', 'Status', 'Endpoint' ], 100);
    $html .= &ui_columns_row([ 'Incoming', 'RTMP ingest', 'listening on configured port', &html_escape("rtmp://<server>:$incoming_port/") ]);
    foreach my $stream (@{$data->{'streams'} || []}) {
        my $state = $stream->{'enabled'} ? 'active' : 'inactive';
        my $endpoint = restreamconf_normalize_stream_url($stream->{'url'} || '', $stream->{'key'} || '');
        $html .= &ui_columns_row([ 'Outgoing', &html_escape($stream->{'name'} || $stream->{'id'}), $state, &html_escape($endpoint || '-') ]);
    }
    $html .= &ui_columns_end();
    return $html;
}

1;
