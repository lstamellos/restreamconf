use strict;
use warnings;
use Test::More;
use FindBin;
use lib "$FindBin::Bin/lib";
no warnings qw(once redefine);

require "$FindBin::Bin/../restreamconf-lib.pl";

sub sample_data {
    my (%overrides) = @_;
    my $data = {
        incoming_host => 'stream.example.test',
        incoming_port => 1935,
        inputs => [ {
            id => 'input_default',
            name => 'Default input',
            incoming_host => 'stream.example.test',
            incoming_port => 1935,
        } ],
        groups => [ { id => 'default', enabled => 1, name => 'Default group' } ],
        streams => [ {
            id => 'youtube',
            enabled => 1,
            name => 'YouTube',
            protocol => 'rtmps',
            url => 'rtmps://example.test/live',
            key => 'key',
            group_id => 'default',
            input_id => 'input_default',
        } ],
    };
    $data->{$_} = $overrides{$_} foreach keys(%overrides);
    return $data;
}

{
    local %main::config = (
        nginx_binary => '/usr/sbin/nginx',
        nginx_conf => '/etc/nginx/restreamconf/nginx.conf',
        nginx_pid => '/run/restreamconf-nginx.pid',
        nginx_prefix => '/var/lib/restreamconf/nginx',
    );
    my $unit = restreamconf_nginx_systemd_unit();
    like($unit, qr/^PIDFile=\/run\/restreamconf-nginx\.pid$/m, 'systemd unit tracks the isolated nginx PID');
    like($unit, qr/^WantedBy=multi-user\.target$/m, 'systemd unit can be enabled at boot');
    unlike($unit, qr/nginx\.service/, 'systemd unit does not control the host nginx service');
}

{
    local %main::config = (local_rtmps_base_port => 65535);
    local *main::restreamconf_managed_stunnel_ports = sub { () };
    local *main::restreamconf_listening_pids_for_port = sub { () };
    my $data = sample_data(streams => [
        sample_data()->{'streams'}->[0],
        { %{sample_data()->{'streams'}->[0]}, id => 'second' },
    ]);
    my @errors = restreamconf_validate_configuration($data);
    ok(grep(/overflows 65535/, @errors), 'overflowing local RTMPS ranges are rejected');
}

{
    local %main::config = (local_rtmps_base_port => 1935);
    local *main::restreamconf_managed_stunnel_ports = sub { () };
    local *main::restreamconf_listening_pids_for_port = sub { () };
    my @errors = restreamconf_validate_configuration(sample_data());
    ok(grep(/conflicts with an incoming RTMP port/, @errors), 'incoming and local RTMPS port overlap is rejected');
}

{
    local %main::config = (local_rtmps_base_port => 19350);
    local *main::restreamconf_managed_stunnel_ports = sub { () };
    local *main::restreamconf_listening_pids_for_port = sub { () };
    my $stream = sample_data()->{'streams'}->[0];
    my $data = sample_data(streams => [ $stream, { %{$stream} } ]);
    my @errors = restreamconf_validate_configuration($data);
    ok(grep(/Duplicate stream ID/, @errors), 'duplicate stream IDs are rejected');
}

{
    local *main::restreamconf_listening_pids_for_port = sub { (424242) };
    local *main::restreamconf_pid_owns_stunnel_config = sub { 0 };
    my @signals;
    local *main::restreamconf_signal_pids = sub { push(@signals, [ @_ ]); return 1; };
    my ($released, $blocked) = restreamconf_release_stunnel_ports(sample_data(), 19350);
    is(scalar(@signals), 0, 'unverified listener receives no signal');
    is_deeply($released, [], 'unverified listener is not reported as released');
    is_deeply($blocked, [19350], 'unverified listener is reported as blocked');
}

{
    local %main::config = (local_rtmps_base_port => 19350);
    local *main::restreamconf_managed_stunnel_ports = sub { () };
    local *main::restreamconf_listening_pids_for_port = sub { $_[0] == 1935 ? (777) : () };
    local *main::restreamconf_pid_is_isolated_nginx = sub { 0 };
    my @errors = restreamconf_validate_configuration(sample_data(streams => []));
    ok(grep(/Incoming port 1935 is already used.*PID 777/, @errors), 'foreign listeners on incoming ports are rejected');
}

{
    local %main::config = (
        local_rtmps_base_port => 19350,
        nginx_binary => '/usr/sbin/nginx',
        nginx_conf => '/etc/nginx/restreamconf/nginx.conf',
        nginx_pid => '/run/restreamconf-nginx.pid',
        nginx_prefix => '/var/lib/restreamconf/nginx',
        restream_nginx_service => 'restreamconf-nginx.service',
        stunnel_service => 'stunnel4',
    );
    my @commands;
    local *main::restreamconf_validate_configuration = sub { () };
    local *main::restreamconf_managed_stunnel_ports = sub { (19350) };
    local *main::restreamconf_write_service_files = sub { 1 };
    local *main::restreamconf_service_active = sub { 'active' };
    local *main::restreamconf_release_stunnel_ports = sub { ([], []) };
    local *main::restreamconf_stunnel_has_other_service_configs = sub { 0 };
    local *main::restreamconf_command_output = sub { push(@commands, join(' ', @_)); return (0, ''); };
    restreamconf_apply_services(sample_data(streams => []));
    ok(grep(/^systemctl daemon-reload$/, @commands), 'apply reloads systemd after writing the unit');
    ok(grep(/^systemctl enable restreamconf-nginx\.service$/, @commands), 'apply enables isolated nginx at boot');
    ok(grep(/^systemctl reload restreamconf-nginx\.service$/, @commands), 'apply reloads the isolated nginx service');
    ok(grep(/^systemctl stop stunnel4$/, @commands), 'removing the last RTMPS destination stops stale stunnel listeners');
}

done_testing();
