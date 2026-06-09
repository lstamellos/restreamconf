#!/usr/bin/perl

require './restreamconf-lib.pl';

&ReadParse();
&ui_print_header(undef, $text{'save_title'} || 'Save Restream Configuration', '', undef, 1, 1);

my $data = {
    inputs => [],
    groups => [],
    streams => [],
};

my %input_ids;
my %input_ports;
my $input_rows = int($in{'input_rows'} || 0);
for (my $i = 0; $i < $input_rows; $i++) {
    my $name = $in{"input_name_$i"} || '';
    my $incoming_host = $in{"input_host_$i"} || '';
    my $incoming_port = $in{"input_port_$i"};
    $name =~ s/^\s+|\s+$//g;
    $incoming_host =~ s/^\s+|\s+$//g;
    next if ($name eq '' && $incoming_host eq '' && (!defined($incoming_port) || $incoming_port eq ''));

    &error('Public incoming stream hostname is required for input ' . ($i + 1)) if ($incoming_host eq '');
    &error('Public incoming stream hostname contains unsupported characters for input ' . ($i + 1)) if (!restreamconf_valid_host($incoming_host));
    &error('Incoming stream port must be between 1 and 65535 for input ' . ($i + 1)) if (!restreamconf_valid_port($incoming_port));
    &error('Incoming stream port ' . int($incoming_port) . ' is used by more than one input') if ($input_ports{int($incoming_port)});

    my $id = $in{"input_id_$i"} || restreamconf_new_id('input', $i);
    $id =~ s/[^A-Za-z0-9_.-]/_/g;
    next if ($input_ids{$id});
    push(@{$data->{'inputs'}}, {
        id => $id,
        name => $name || 'Input ' . ($i + 1),
        incoming_host => $incoming_host,
        incoming_port => int($incoming_port),
    });
    $input_ids{$id} = 1;
    $input_ports{int($incoming_port)} = 1;
}

if (!@{$data->{'inputs'}}) {
    &error('At least one incoming stream input is required');
}
$data->{'incoming_host'} = $data->{'inputs'}->[0]->{'incoming_host'};
$data->{'incoming_port'} = $data->{'inputs'}->[0]->{'incoming_port'};
my $fallback_input = $data->{'inputs'}->[0]->{'id'};

my %group_ids;
my %pending_groups;
my @pending_group_order;
my $group_rows = int($in{'group_rows'} || 0);
for (my $i = 0; $i < $group_rows; $i++) {
    my $name = $in{"group_name_$i"} || '';
    $name =~ s/^\s+|\s+$//g;

    my $id = $in{"group_id_$i"} || restreamconf_new_id('group', $i);
    $id =~ s/[^A-Za-z0-9_.-]/_/g;
    next if ($pending_groups{$id});
    $pending_groups{$id} = {
        id => $id,
        enabled => $in{"group_enabled_$i"} ? 1 : 0,
        name => $name,
        index => $i,
    };
    push(@pending_group_order, $id);

    next if ($name eq '');
    push(@{$data->{'groups'}}, {
        id => $id,
        enabled => $pending_groups{$id}->{'enabled'},
        name => $name,
    });
    $group_ids{$id} = 1;
}

if (!@{$data->{'groups'}}) {
    my $default_id = $pending_group_order[0] || restreamconf_default_group_id();
    my $default_group = $pending_groups{$default_id} || { id => $default_id, enabled => 1, name => 'Default group' };
    push(@{$data->{'groups'}}, {
        id => $default_group->{'id'},
        enabled => $default_group->{'enabled'} ? 1 : 0,
        name => $default_group->{'name'} || 'Default group',
    });
    $group_ids{$default_group->{'id'}} = 1;
}

my $fallback_group = $data->{'groups'}->[0]->{'id'};
my $rows = int($in{'rows'} || 0);
for (my $i = 0; $i < $rows; $i++) {
    my $name = $in{"name_$i"} || '';
    my $url = $in{"url_$i"} || '';
    my $key = $in{"key_$i"} || '';
    $name =~ s/^\s+|\s+$//g;
    $url =~ s/^\s+|\s+$//g;
    $key =~ s/^\s+|\s+$//g;
    next if ($name eq '' && $url eq '' && $key eq '');

    my $protocol = lc($in{"protocol_$i"} || 'rtmp');
    &error("Invalid protocol for row " . ($i + 1)) if ($protocol ne 'rtmp' && $protocol ne 'rtmps');
    my $full_url = restreamconf_normalize_stream_url($url, '');
    &error("Stream URL is required for row " . ($i + 1)) if ($full_url eq '');
    &error("Stream URL for row " . ($i + 1) . " must start with $protocol://") if ($full_url !~ /^\Q$protocol\E:\/\//i);
    &error("Stream URL for row " . ($i + 1) . " contains characters that are unsafe for nginx configuration") if ($full_url =~ /[\s;{}]/);
    &error("Stream key for row " . ($i + 1) . " contains characters that are unsafe for nginx configuration") if ($key =~ /[\s;{}]/);
    my $parsed = restreamconf_parse_rtmp_url(restreamconf_normalize_stream_url($url, $key));
    &error("Stream URL for row " . ($i + 1) . " must include a valid RTMP or RTMPS host") if (!$parsed);
    &error("Stream URL port for row " . ($i + 1) . " is outside the valid range") if (!restreamconf_valid_port($parsed->{'port'}));

    my $group_id = $in{"group_$i"} || $fallback_group;
    $group_id =~ s/[^A-Za-z0-9_.-]/_/g;
    if (!$group_ids{$group_id} && $pending_groups{$group_id}) {
        my $pending_group = $pending_groups{$group_id};
        push(@{$data->{'groups'}}, {
            id => $group_id,
            enabled => $pending_group->{'enabled'} ? 1 : 0,
            name => $pending_group->{'name'} || 'Group ' . ($pending_group->{'index'} + 1),
        });
        $group_ids{$group_id} = 1;
    }
    $group_id = $fallback_group if (!$group_ids{$group_id});

    my $input_id = $in{"input_$i"} || $fallback_input;
    $input_id =~ s/[^A-Za-z0-9_.-]/_/g;
    $input_id = $fallback_input if (!$input_ids{$input_id});

    push(@{$data->{'streams'}}, {
        id => $in{"id_$i"} || restreamconf_new_id('stream', $i),
        enabled => $in{"enabled_$i"} ? 1 : 0,
        name => $name || "Stream " . ($i + 1),
        protocol => $protocol,
        url => $url,
        key => $key,
        group_id => $group_id,
        input_id => $input_id,
    });
}

restreamconf_write_config($data);
print '<p>Configuration saved.</p>';

if (defined($in{'apply'})) {
    print '<h3>Service apply results</h3><ul>';
    my @messages = restreamconf_apply_services($data);
    foreach my $message (@messages) {
        print '<li>' . &html_escape($message) . '</li>';
    }
    print '</ul>';
}
else {
    restreamconf_write_service_files($data);
    print '<p>Generated nginx and stunnel4 configuration files. Restart services when ready, or use <b>Save and apply</b>.</p>';
}

print '<p>' . &ui_link('index.cgi', 'Return to Restream Configuration') . '</p>';
&ui_print_footer('', '');
