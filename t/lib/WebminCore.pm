package WebminCore;

use strict;
use warnings;
use Exporter 'import';

our @EXPORT = qw(init_config make_dir error html_escape);

sub init_config {
    $main::config_directory ||= '/tmp/restreamconf-test';
}

sub make_dir {
    my ($path) = @_;
    mkdir($path) if ($path && !-d $path);
}

sub error { die $_[0]; }

sub html_escape {
    my ($value) = @_;
    $value = '' if (!defined($value));
    $value =~ s/&/&amp;/g;
    $value =~ s/</&lt;/g;
    $value =~ s/>/&gt;/g;
    $value =~ s/"/&quot;/g;
    return $value;
}

1;
