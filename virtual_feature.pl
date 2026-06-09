# virtual_feature.pl - Virtualmin integration hooks for restreamconf.

require './restreamconf-lib.pl';

sub feature_name
{
    return 'Restream Configuration';
}

sub feature_label
{
    return 'Enable RTMP/RTMPS restream configuration';
}

sub feature_suitable
{
    return 1;
}

sub feature_check
{
    return undef;
}

sub settings_links
{
    return ( { 'link' => '/restreamconf/index.cgi',
               'title' => 'Restream Configuration',
               'icon' => '/restreamconf/images/icon.gif',
               'cat' => 'services' } );
}

sub theme_sections
{
    my $data = restreamconf_read_config();
    my $nginx = restreamconf_service_active($config{'nginx_service'} || 'nginx');
    my $stunnel = restreamconf_service_active($config{'stunnel_service'} || 'stunnel4');
    my $html = '<div><b>nginx:</b> ' . &html_escape($nginx) .
               ' &nbsp; <b>stunnel4:</b> ' . &html_escape($stunnel) . '</div>';
    $html .= restreamconf_render_status_table($data);
    $html .= restreamconf_monitor_assets();
    $html .= '<p><a href="/restreamconf/dashboard.cgi">View restream monitor</a></p>';
    return ( { 'title' => 'RTMP/RTMPS Restream Status',
               'html' => $html,
               'status' => 1,
               'for_master' => 1,
               'for_reseller' => 0,
               'for_owner' => 0 } );
}

1;
