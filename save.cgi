#!/usr/bin/perl

require './restreamconf-lib.pl';

&ReadParse();
&ui_print_header(undef, $text{'save_title'} || 'Save Restream Configuration', '', undef, 1, 1);

my $incoming_host = $in{'incoming_host'} || '';
$incoming_host =~ s/^\s+|\s+$//g;
&error('Public incoming stream hostname is required') if ($incoming_host eq '');
&error('Public incoming stream hostname contains unsupported characters') if (!restreamconf_valid_host($incoming_host));

my $incoming_port = $in{'incoming_port'};
&error('Incoming stream port must be between 1 and 65535') if (!restreamconf_valid_port($incoming_port));

my $data = {
    incoming_host => $incoming_host,
    incoming_port => int($incoming_port),
    streams => [],
};

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

    push(@{$data->{'streams'}}, {
        id => $in{"id_$i"} || time() . "_$i",
        enabled => $in{"enabled_$i"} ? 1 : 0,
        name => $name || "Stream " . ($i + 1),
        protocol => $protocol,
        url => $url,
        key => $key,
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
