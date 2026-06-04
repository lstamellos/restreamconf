#!/usr/bin/perl

require './restreamconf-lib.pl';

&ui_print_header(undef, $text{'dashboard_title'} || 'Restream Status', '', undef, 1, 1);

my $data = restreamconf_read_config();
print '<h3>Services</h3>';
print &ui_columns_start([ 'Service', 'Status' ], 100);
print &ui_columns_row([ $config{'nginx_service'} || 'nginx', restreamconf_service_active($config{'nginx_service'} || 'nginx') ]);
print &ui_columns_row([ $config{'stunnel_service'} || 'stunnel4', restreamconf_service_active($config{'stunnel_service'} || 'stunnel4') ]);
print &ui_columns_end();

print '<h3>Streams</h3>';
print restreamconf_render_status_table($data);
print '<p>Inactive outgoing configurations are retained and shown here as inactive so they can be re-enabled later.</p>';

&ui_print_footer('index.cgi', 'Restream Configuration');
