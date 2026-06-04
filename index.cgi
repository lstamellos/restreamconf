#!/usr/bin/perl

require './restreamconf-lib.pl';

&ui_print_header(undef, $text{'index_title'} || 'Restream Configuration', '', undef, 1, 1);

my $data = restreamconf_read_config();
my @streams = @{$data->{'streams'} || []};
my $rows = @streams + 3;

print &ui_form_start('save.cgi', 'post');
print &ui_table_start('Incoming stream', undef, 2);
print &ui_table_row('Incoming RTMP port', &ui_textbox('incoming_port', $data->{'incoming_port'} || 1935, 8));
print &ui_table_row('Application name', '<code>' . ($config{'application'} || 'live') . '</code>');
print &ui_table_end();

print '<h3>Outgoing streams</h3>';
print '<p>Configure each RTMP or RTMPS destination separately. RTMPS destinations are proxied through module-owned stunnel4 services, while RTMP destinations are pushed directly by nginx.</p>';
print '<table class="ui_table" width="100%">';
print '<tr><th>Enabled</th><th>Name</th><th>Protocol</th><th>Stream URL</th><th>Stream key</th></tr>';

for (my $i = 0; $i < $rows; $i++) {
    my $stream = $streams[$i] || {};
    my $id = $stream->{'id'} || time() . "_$i";
    print '<tr>';
    print '<td>' . &ui_hidden("id_$i", $id) . &ui_checkbox("enabled_$i", 1, '', $stream->{'enabled'}) . '</td>';
    print '<td>' . &ui_textbox("name_$i", $stream->{'name'} || '', 18) . '</td>';
    print '<td>' . &ui_select("protocol_$i", $stream->{'protocol'} || 'rtmp', [ [ 'rtmp', 'RTMP' ], [ 'rtmps', 'RTMPS' ] ]) . '</td>';
    print '<td>' . &ui_textbox("url_$i", $stream->{'url'} || '', 45) . '</td>';
    print '<td>' . &ui_textbox("key_$i", $stream->{'key'} || '', 24) . '</td>';
    print '</tr>';
}
print '</table>';
print &ui_hidden('rows', $rows);
print &ui_form_end([ [ 'save', 'Save' ], [ 'apply', 'Save and apply' ] ]);

print '<h3>Monitoring</h3>';
print restreamconf_render_status_table($data);
print '<p><a href="dashboard.cgi">Open standalone monitoring view</a></p>';

&ui_print_footer('', '');
