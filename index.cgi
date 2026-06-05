#!/usr/bin/perl

require './restreamconf-lib.pl';

&ui_print_header(undef, $text{'index_title'} || 'Restream Configuration', '', undef, 1, 1);

my $data = restreamconf_read_config();
my @groups = @{$data->{'groups'} || []};
my @streams = @{$data->{'streams'} || []};
my $group_rows = @groups + 2;
my @group_form_rows;
for (my $i = 0; $i < $group_rows; $i++) {
    my $group = $groups[$i] || {};
    my $id = $group->{'id'} || restreamconf_new_id('group', $i);
    push(@group_form_rows, {
        id => $id,
        enabled => defined($group->{'enabled'}) ? $group->{'enabled'} : 1,
        name => $group->{'name'} || '',
    });
}

print &ui_form_start('save.cgi', 'post');
print &ui_table_start('Incoming stream', undef, 2);
print &ui_table_row('Public RTMP hostname', &ui_textbox('incoming_host', $data->{'incoming_host'} || $config{'incoming_host'} || $DEFAULT_INCOMING_HOST, 32));
print &ui_table_row('Incoming RTMP port', &ui_textbox('incoming_port', $data->{'incoming_port'} || 1935, 8));
print &ui_table_row('Application name', '<code>' . ($config{'application'} || 'live') . '</code>');
print &ui_table_end();

print '<h3>Outgoing streams</h3>';
print '<p>Configure each group in its own accordion. A destination only pushes when both its group and its own row are enabled. RTMPS destinations are forwarded through module-owned stunnel4 TLS tunnels, while RTMP destinations are pushed directly by nginx.</p>';

my %streams_by_group;
foreach my $stream (@streams) {
    my $group_id = $stream->{'group_id'} || ($group_form_rows[0] ? $group_form_rows[0]->{'id'} : restreamconf_default_group_id());
    push(@{$streams_by_group{$group_id}}, $stream);
}

my $stream_row = 0;
for (my $group_index = 0; $group_index < $group_rows; $group_index++) {
    my $group = $group_form_rows[$group_index];
    my @group_streams = @{$streams_by_group{$group->{'id'}} || []};
    my $group_stream_rows = @group_streams + 3;
    my $summary_state = $group->{'enabled'} ? 'enabled' : 'disabled';
    my $details_attr = ($group_index < @groups || @group_streams) ? ' open' : '';
    my $stream_count = scalar(@group_streams);

    print '<details class="ui_table restreamconf_group"' . $details_attr . ' style="margin: 1em 0; padding: 0.5em;">';
    print '<summary style="cursor: pointer; font-weight: bold;">Group ' . ($group_index + 1) . ' &mdash; ' . $summary_state . ', ' . $stream_count . ' configured stream' . ($stream_count == 1 ? '' : 's') . '</summary>';
    print '<div style="margin: 0.75em 0;">';
    print &ui_hidden("group_id_$group_index", $group->{'id'});
    print '<b>Group enabled:</b> ' . &ui_checkbox("group_enabled_$group_index", 1, '', $group->{'enabled'});
    print ' &nbsp; <b>Group name:</b> ' . &ui_textbox("group_name_$group_index", $group->{'name'}, 30);
    print '</div>';

    print '<table class="ui_table" width="100%">';
    print '<tr><th>Enabled</th><th>Name</th><th>Protocol</th><th>Stream URL</th><th>Stream key</th></tr>';
    for (my $i = 0; $i < $group_stream_rows; $i++) {
        my $stream = $group_streams[$i] || {};
        my $id = $stream->{'id'} || restreamconf_new_id('stream', $stream_row);
        print '<tr>';
        print '<td>' . &ui_hidden("id_$stream_row", $id) . &ui_hidden("group_$stream_row", $group->{'id'}) . &ui_checkbox("enabled_$stream_row", 1, '', $stream->{'enabled'}) . '</td>';
        print '<td>' . &ui_textbox("name_$stream_row", $stream->{'name'} || '', 18) . '</td>';
        print '<td>' . &ui_select("protocol_$stream_row", $stream->{'protocol'} || 'rtmp', [ [ 'rtmp', 'RTMP' ], [ 'rtmps', 'RTMPS' ] ]) . '</td>';
        print '<td>' . &ui_textbox("url_$stream_row", $stream->{'url'} || '', 45) . '</td>';
        print '<td>' . &ui_textbox("key_$stream_row", $stream->{'key'} || '', 24) . '</td>';
        print '</tr>';
        $stream_row++;
    }
    print '</table>';
    print '</details>';
}
print &ui_hidden('group_rows', $group_rows);
print &ui_hidden('rows', $stream_row);
print &ui_form_end([ [ 'save', 'Save' ], [ 'apply', 'Save and apply' ] ]);

print '<h3>Monitoring</h3>';
print restreamconf_render_status_table($data);
print '<p><a href="dashboard.cgi">Open standalone monitoring view</a>. Diagnostics include nginx config/include checks, listener PIDs, generated stunnel4 actions, and tunnel ports.</p>';

&ui_print_footer('', '');
