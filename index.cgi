#!/usr/bin/perl

require './restreamconf-lib.pl';

&ui_print_header(undef, $text{'index_title'} || 'Restream Configuration', '', undef, 1, 1);

my $data = restreamconf_read_config();
my @groups = @{$data->{'groups'} || []};
my @streams = @{$data->{'streams'} || []};
my $group_rows = @groups + 2;
my $stream_rows = @streams + 3;
my @group_form_rows;
for (my $i = 0; $i < $group_rows; $i++) {
    my $group = $groups[$i] || {};
    my $id = $group->{'id'} || restreamconf_new_id('group', $i);
    push(@group_form_rows, {
        id => $id,
        enabled => defined($group->{'enabled'}) ? $group->{'enabled'} : 1,
        name => $group->{'name'} || '',
        label => $group->{'name'} || 'New group ' . ($i + 1),
    });
}

print &ui_form_start('save.cgi', 'post');
print &ui_table_start('Incoming stream', undef, 2);
print &ui_table_row('Public RTMP hostname', &ui_textbox('incoming_host', $data->{'incoming_host'} || $config{'incoming_host'} || $DEFAULT_INCOMING_HOST, 32));
print &ui_table_row('Incoming RTMP port', &ui_textbox('incoming_port', $data->{'incoming_port'} || 1935, 8));
print &ui_table_row('Application name', '<code>' . ($config{'application'} || 'live') . '</code>');
print &ui_table_end();

print '<h3>Outgoing stream groups</h3>';
print '<p>Groups let you enable or disable several outgoing destinations at once. A destination only pushes when both its group and its own row are enabled.</p>';
print '<table class="ui_table" width="100%">';
print '<tr><th>Enabled</th><th>Group name</th></tr>';
for (my $i = 0; $i < $group_rows; $i++) {
    my $group = $group_form_rows[$i];
    print '<tr>';
    print '<td>' . &ui_hidden("group_id_$i", $group->{'id'}) . &ui_checkbox("group_enabled_$i", 1, '', $group->{'enabled'}) . '</td>';
    print '<td>' . &ui_textbox("group_name_$i", $group->{'name'}, 30) . '</td>';
    print '</tr>';
}
print '</table>';
print &ui_hidden('group_rows', $group_rows);

my @group_options = map { [ $_->{'id'}, $_->{'label'} ] } @group_form_rows;

print '<h3>Outgoing streams</h3>';
print '<p>Configure each RTMP or RTMPS destination separately and assign it to a group. RTMPS destinations are forwarded through module-owned stunnel4 TLS tunnels, while RTMP destinations are pushed directly by nginx.</p>';
print '<table class="ui_table" width="100%">';
print '<tr><th>Enabled</th><th>Group</th><th>Name</th><th>Protocol</th><th>Stream URL</th><th>Stream key</th></tr>';

for (my $i = 0; $i < $stream_rows; $i++) {
    my $stream = $streams[$i] || {};
    my $id = $stream->{'id'} || restreamconf_new_id('stream', $i);
    my $selected_group = $stream->{'group_id'} || ($group_options[0] ? $group_options[0]->[0] : restreamconf_default_group_id());
    print '<tr>';
    print '<td>' . &ui_hidden("id_$i", $id) . &ui_checkbox("enabled_$i", 1, '', $stream->{'enabled'}) . '</td>';
    print '<td>' . &ui_select("group_$i", $selected_group, \@group_options) . '</td>';
    print '<td>' . &ui_textbox("name_$i", $stream->{'name'} || '', 18) . '</td>';
    print '<td>' . &ui_select("protocol_$i", $stream->{'protocol'} || 'rtmp', [ [ 'rtmp', 'RTMP' ], [ 'rtmps', 'RTMPS' ] ]) . '</td>';
    print '<td>' . &ui_textbox("url_$i", $stream->{'url'} || '', 45) . '</td>';
    print '<td>' . &ui_textbox("key_$i", $stream->{'key'} || '', 24) . '</td>';
    print '</tr>';
}
print '</table>';
print &ui_hidden('rows', $stream_rows);
print &ui_form_end([ [ 'save', 'Save' ], [ 'apply', 'Save and apply' ] ]);

print '<h3>Monitoring</h3>';
print restreamconf_render_status_table($data);
print '<p><a href="dashboard.cgi">Open standalone monitoring view</a>. Diagnostics include nginx config/include checks, listener PIDs, generated stunnel4 actions, and tunnel ports.</p>';

&ui_print_footer('', '');
