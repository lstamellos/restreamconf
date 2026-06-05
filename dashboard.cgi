#!/usr/bin/perl

require './restreamconf-lib.pl';

&ui_print_header(undef, $text{'dashboard_title'} || 'Restream Status', '', undef, 1, 1);

my $data = restreamconf_read_config();
print '<h3>Services</h3>';
print &ui_columns_start([ 'Service', 'Status' ], 100);
my $nginx_service = restreamconf_safe_service_name($config{'nginx_service'} || 'nginx', 'nginx');
my $stunnel_service = restreamconf_safe_service_name($config{'stunnel_service'} || 'stunnel4', 'stunnel4');
print &ui_columns_row([ &html_escape($nginx_service), &html_escape(restreamconf_service_active($nginx_service)) ]);
print &ui_columns_row([ &html_escape($stunnel_service), &html_escape(restreamconf_service_active($stunnel_service)) ]);
print &ui_columns_end();

print '<h3>Streams</h3>';
print restreamconf_render_status_table($data);
print '<p>Inactive outgoing configurations are retained and shown here as inactive so they can be re-enabled later.</p>';
print restreamconf_render_diagnostics($data);

&ui_print_footer('index.cgi', 'Restream Configuration');
