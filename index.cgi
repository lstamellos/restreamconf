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
        is_existing => $i < @groups ? 1 : 0,
    });
}

my %streams_by_group;
foreach my $stream (@streams) {
    my $group_id = $stream->{'group_id'} || ($group_form_rows[0] ? $group_form_rows[0]->{'id'} : restreamconf_default_group_id());
    push(@{$streams_by_group{$group_id}}, $stream);
}

sub restreamconf_icon_button {
    my ($class, $label, $icon, $title, $attrs) = @_;
    $attrs ||= '';
    my $value = $icon . ' ' . $label;
    return '<input type="button" class="' . &html_escape($class) . '" value="' . &html_escape($value) . '" title="' . &html_escape($title) . '" aria-label="' . &html_escape($title) . '" ' . $attrs . '>';
}

sub restreamconf_status_badges {
    my ($enabled, $active) = @_;
    return '<span class="rc-badges"><span class="rc-badge rc-enabled-badge">' . ($enabled ? 'Enabled' : 'Disabled') . '</span> ' .
        '<span class="rc-badge rc-active-badge">' . ($active ? 'Active' : 'Inactive') . '</span></span>';
}

sub restreamconf_stream_row_html {
    my ($stream_row, $group_id, $stream, $is_blank, $data) = @_;
    $stream ||= {};
    my $id = $stream->{'id'} || restreamconf_new_id('stream', $stream_row);
    my $row_class = $is_blank ? ' rc-empty-row' : '';
    my $enabled = defined($stream->{'enabled'}) ? $stream->{'enabled'} : 1;
    my $active = (!$is_blank && restreamconf_stream_active($data, $stream)) ? 1 : 0;
    my $html = '<tr class="rc-stream-row' . $row_class . '" data-row-index="' . int($stream_row) . '">';
    $html .= '<td class="rc-stream-actions">' . &ui_hidden("id_$stream_row", $id) . &ui_hidden("group_$stream_row", $group_id) . &ui_checkbox("enabled_$stream_row", 1, '', $enabled) . '</td>';
    $html .= '<td><span class="rc-name-with-badges">' . &ui_textbox("name_$stream_row", $stream->{'name'} || '', 18) . ' ' . restreamconf_status_badges($enabled, $active) . '</span></td>';
    $html .= '<td>' . &ui_select("protocol_$stream_row", $stream->{'protocol'} || 'rtmp', [ [ 'rtmp', 'RTMP' ], [ 'rtmps', 'RTMPS' ] ]) . '</td>';
    $html .= '<td>' . &ui_textbox("url_$stream_row", $stream->{'url'} || '', 45) . '</td>';
    $html .= '<td>' . &ui_textbox("key_$stream_row", $stream->{'key'} || '', 24) . '</td>';
    $html .= '<td class="rc-row-tools">' . restreamconf_icon_button('rc-remove-stream', 'Remove', '🗑️', 'Remove this configuration') . '</td>';
    $html .= '</tr>';
    return $html;
}
print <<'STYLE';
<style>
.rc-shell { max-width: 1220px; }
.rc-intro { line-height: 1.5; max-width: 920px; }
.rc-tabs { display: flex; flex-wrap: wrap; gap: .25em; margin: 1em 0; }
.rc-tab[aria-selected="true"] { font-weight: bold; text-decoration: underline; }
.rc-tab-panel { display: none; }
.rc-tab-panel.rc-active { display: block; }
.rc-section-title { align-items: center; display: flex; gap: .5em; justify-content: space-between; margin: 0 0 .75em; }
.rc-section-title h3 { margin-bottom: 0; }
.rc-group { margin: 1em 0; padding: .25em; }
.rc-group[hidden] { display: none; }
.rc-group-summary { align-items: center; cursor: pointer; display: flex; gap: .75em; justify-content: space-between; padding: .35em; }
.rc-group-heading { align-items: center; display: flex; flex-wrap: wrap; gap: .5em; min-width: 0; }
.rc-group-title { font-weight: bold; }
.rc-badges { white-space: nowrap; }
.rc-badge, .rc-stream-count { font-size: .9em; }
.rc-name-with-badges { align-items: center; display: flex; flex-wrap: wrap; gap: .35em; }
.rc-group-tools, .rc-toolbar, .rc-row-tools { align-items: center; display: flex; flex-wrap: wrap; gap: .35em; }
.rc-group-body { padding: .5em .25em .25em; }
.rc-group:not([open]) .rc-group-body { display: none; }
.rc-group-fields { align-items: center; display: flex; flex-wrap: wrap; gap: .75em 1.25em; margin-bottom: .75em; }
.rc-stream-table { width: 100%; }
.rc-stream-table th, .rc-stream-table td { padding: .35em; vertical-align: middle; }
.rc-stream-table input[type="text"] { max-width: 100%; }
.rc-monitor-link { font-weight: bold; }
@media (max-width: 760px) { .rc-stream-table { display: block; overflow-x: auto; } }
</style>
STYLE

print &ui_form_start('save.cgi', 'post');
print '<div class="rc-shell">';
print '<p class="rc-intro">Use the tabs below to move between incoming stream settings, destination groups, and monitoring. Groups use accordions so you can focus on one set of outgoing configurations at a time.</p>';

print '<div class="rc-tabs" role="tablist" aria-label="Restream configuration sections">';
print '<input type="button" class="rc-tab" role="tab" aria-selected="true" aria-controls="rc-panel-incoming" id="rc-tab-incoming" data-tab-target="rc-panel-incoming" value="📥 Incoming">';
print '<input type="button" class="rc-tab" role="tab" aria-selected="false" aria-controls="rc-panel-destinations" id="rc-tab-destinations" data-tab-target="rc-panel-destinations" value="📡 Destinations">';
print '<input type="button" class="rc-tab" role="tab" aria-selected="false" aria-controls="rc-panel-monitoring" id="rc-tab-monitoring" data-tab-target="rc-panel-monitoring" value="📊 Monitoring">';
print '</div>';

print '<section class="rc-tab-panel rc-active" role="tabpanel" id="rc-panel-incoming" aria-labelledby="rc-tab-incoming">';
print '<div class="rc-section-title"><h3>📥 Incoming stream</h3></div>';
print &ui_table_start('Incoming stream', undef, 2);
print &ui_table_row('Public RTMP hostname', &ui_textbox('incoming_host', $data->{'incoming_host'} || $config{'incoming_host'} || $DEFAULT_INCOMING_HOST, 32));
print &ui_table_row('Incoming RTMP port', &ui_textbox('incoming_port', $data->{'incoming_port'} || 1935, 8));
print &ui_table_row('Application name', '<code>' . &html_escape($config{'application'} || 'live') . '</code>');
print &ui_table_end();
print '</section>';

print '<section class="rc-tab-panel" role="tabpanel" id="rc-panel-destinations" aria-labelledby="rc-tab-destinations">';
print '<div class="rc-section-title"><h3>📡 Outgoing destinations</h3><div class="rc-toolbar">' . restreamconf_icon_button('rc-add-group', 'Add group', '➕', 'Add a new group', 'id="rc-add-group"') . '</div></div>';
print '<p class="rc-intro">Configure each destination group in its own accordion. A destination only pushes when both its group and its own row are enabled. RTMPS destinations are forwarded through module-owned stunnel4 TLS tunnels, while RTMP destinations are pushed directly by nginx.</p>';
print '<div id="rc-groups">';

my $stream_row = 0;
for (my $group_index = 0; $group_index < $group_rows; $group_index++) {
    my $group = $group_form_rows[$group_index];
    my @group_streams = @{$streams_by_group{$group->{'id'}} || []};
    my $summary_state = $group->{'enabled'} ? 'Enabled' : 'Disabled';
    my $group_active = 0;
    foreach my $group_stream (@group_streams) {
        if (restreamconf_stream_active($data, $group_stream)) {
            $group_active = 1;
            last;
        }
    }
    my $active_state = $group_active ? 'Active' : 'Inactive';
    my $details_attr = '';
    my $hidden_attr = (!$group->{'is_existing'} && !@group_streams && $group->{'name'} eq '') ? ' hidden' : '';
    my $stream_count = scalar(@group_streams);
    my $title = $group->{'name'} || 'New group ' . ($group_index + 1);

    print '<details class="ui_table rc-group" data-group-index="' . int($group_index) . '" data-group-id="' . &html_escape($group->{'id'}) . '"' . $details_attr . $hidden_attr . '>';
    print '<summary class="rc-group-summary">';
    print '<span class="rc-group-heading"><span class="rc-caret" aria-hidden="true">▸</span><span class="rc-group-title">' . &html_escape($title) . '</span><span class="rc-badge rc-enabled-badge">' . $summary_state . '</span><span class="rc-badge rc-active-badge">' . $active_state . '</span><span class="rc-stream-count">' . int($stream_count) . ' stream' . ($stream_count == 1 ? '' : 's') . '</span></span>';
    print '<span class="rc-group-tools">' . restreamconf_icon_button('rc-edit-group', 'Edit', '✏️', 'Edit this group') . restreamconf_icon_button('rc-add-stream', 'Add config', '➕', 'Add a stream configuration to this group') . restreamconf_icon_button('rc-remove-group', 'Remove', '🗑️', 'Remove this group') . '</span>';
    print '</summary>';
    print '<div class="rc-group-body">';
    print &ui_hidden("group_id_$group_index", $group->{'id'});
    print '<div class="rc-group-fields">';
    print '<label><b>Enabled</b> ' . &ui_checkbox("group_enabled_$group_index", 1, '', $group->{'enabled'}) . '</label>';
    print '<label><b>Group name</b> ' . &ui_textbox("group_name_$group_index", $group->{'name'}, 30) . '</label>';
    print '</div>';
    print '<table class="ui_table rc-stream-table"><thead><tr><th>Enabled</th><th>Name</th><th>Protocol</th><th>Stream URL</th><th>Stream key</th><th>Actions</th></tr></thead><tbody>';
    foreach my $stream (@group_streams) {
        print restreamconf_stream_row_html($stream_row, $group->{'id'}, $stream, 0, $data);
        $stream_row++;
    }
    print restreamconf_stream_row_html($stream_row, $group->{'id'}, {}, 1, $data);
    $stream_row++;
    print '</tbody></table>';
    print '</div></details>';
}
print '</div>';
print &ui_hidden('group_rows', $group_rows);
print &ui_hidden('rows', $stream_row);
print '</section>';

print '<section class="rc-tab-panel" role="tabpanel" id="rc-panel-monitoring" aria-labelledby="rc-tab-monitoring">';
print '<div class="rc-section-title"><h3>📊 Monitoring</h3></div>';
print restreamconf_render_status_table($data);
print '<p><a class="rc-monitor-link" href="dashboard.cgi">Open standalone monitoring view</a>. Diagnostics include nginx config/include checks, listener PIDs, generated stunnel4 actions, and tunnel ports.</p>';
print '</section>';

print &ui_form_end([ [ 'save', 'Save' ], [ 'apply', 'Save and apply' ] ]);
print '</div>';

print <<'SCRIPT';
<script>
(function() {
  function qs(selector, root) { return (root || document).querySelector(selector); }
  function qsa(selector, root) { return Array.prototype.slice.call((root || document).querySelectorAll(selector)); }
  function esc(value) { return String(value).replace(/[&<>"']/g, function(ch) { return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]; }); }
  function nextRows() { return qs('input[name="rows"]'); }
  function nextGroups() { return qs('input[name="group_rows"]'); }
  function activateTab(button) {
    qsa('.rc-tab').forEach(function(tab) { tab.setAttribute('aria-selected', tab === button ? 'true' : 'false'); });
    qsa('.rc-tab-panel').forEach(function(panel) { panel.classList.toggle('rc-active', panel.id === button.getAttribute('data-tab-target')); });
  }
  function rowHasConfig(row) {
    var name = qs('input[name^="name_"]', row);
    var url = qs('input[name^="url_"]', row);
    var key = qs('input[name^="key_"]', row);
    return (name && name.value.trim()) || (url && url.value.trim()) || (key && key.value.trim());
  }
  function rowIsActive(row, groupEnabled) {
    var enabled = qs('input[name^="enabled_"]', row);
    var url = qs('input[name^="url_"]', row);
    return !!(groupEnabled && enabled && enabled.checked && url && url.value.trim());
  }
  function updateBadge(badge, activeText, inactiveText, isActive) {
    if (badge) badge.textContent = isActive ? activeText : inactiveText;
  }
  function updateStreamBadges(group) {
    var groupEnabled = !!(qs('input[name^="group_enabled_"]', group) || {}).checked;
    qsa('.rc-stream-row', group).forEach(function(row) {
      var enabled = qs('input[name^="enabled_"]', row);
      updateBadge(qs('.rc-enabled-badge', row), 'Enabled', 'Disabled', !!(enabled && enabled.checked));
      updateBadge(qs('.rc-active-badge', row), 'Active', 'Inactive', rowIsActive(row, groupEnabled));
    });
  }
  function updateGroupSummary(group) {
    var nameInput = qs('input[name^="group_name_"]', group);
    var enabledInput = qs('input[name^="group_enabled_"]', group);
    var summary = qs('.rc-group-summary', group);
    var title = qs('.rc-group-title', summary);
    var rows = qsa('.rc-stream-row', group);
    var count = rows.filter(rowHasConfig).length;
    var groupEnabled = !!(enabledInput && enabledInput.checked);
    var groupActive = rows.some(function(row) { return rowIsActive(row, groupEnabled); });
    if (title && nameInput) title.textContent = nameInput.value.trim() || 'New group ' + (Number(group.getAttribute('data-group-index')) + 1);
    updateBadge(qs('.rc-enabled-badge', summary), 'Enabled', 'Disabled', groupEnabled);
    updateBadge(qs('.rc-active-badge', summary), 'Active', 'Inactive', groupActive);
    var countEl = qs('.rc-stream-count', group);
    if (countEl) countEl.textContent = count + ' stream' + (count === 1 ? '' : 's');
    updateStreamBadges(group);
  }
  function streamRowHtml(rowIndex, groupId) {
    var safeGroup = esc(groupId);
    return '<tr class="rc-stream-row rc-empty-row" data-row-index="' + rowIndex + '">' +
      '<td class="rc-stream-actions"><input type="hidden" name="id_' + rowIndex + '" value="stream_' + Date.now() + '_' + rowIndex + '"><input type="hidden" name="group_' + rowIndex + '" value="' + safeGroup + '"><input type="checkbox" name="enabled_' + rowIndex + '" value="1" checked></td>' +
      '<td><span class="rc-name-with-badges"><input type="text" name="name_' + rowIndex + '" size="18" value=""> <span class="rc-badges"><span class="rc-badge rc-enabled-badge">Enabled</span> <span class="rc-badge rc-active-badge">Inactive</span></span></span></td>' +
      '<td><select name="protocol_' + rowIndex + '"><option value="rtmp" selected>RTMP</option><option value="rtmps">RTMPS</option></select></td>' +
      '<td><input type="text" name="url_' + rowIndex + '" size="45" value=""></td>' +
      '<td><input type="text" name="key_' + rowIndex + '" size="24" value=""></td>' +
      '<td class="rc-row-tools"><input type="button" class="rc-remove-stream" value="🗑️ Remove" title="Remove this configuration" aria-label="Remove this configuration"></td>' +
      '</tr>';
  }
  function addStream(group) {
    var rowsInput = nextRows();
    var rowIndex = Number(rowsInput.value || 0);
    var tbody = qs('tbody', group);
    tbody.insertAdjacentHTML('beforeend', streamRowHtml(rowIndex, group.getAttribute('data-group-id')));
    rowsInput.value = rowIndex + 1;
    group.open = true;
    updateGroupSummary(group);
  }
  function clearInputs(root) {
    qsa('input[type="text"]', root).forEach(function(input) { input.value = ''; });
    qsa('input[type="checkbox"]', root).forEach(function(input) { input.checked = false; });
    qsa('select', root).forEach(function(select) { select.selectedIndex = 0; });
  }
  function addGroup() {
    var groupsInput = nextGroups();
    var groupIndex = Number(groupsInput.value || 0);
    var groupId = 'group_' + Date.now() + '_' + groupIndex;
    var html = '<details class="ui_table rc-group" data-group-index="' + groupIndex + '" data-group-id="' + esc(groupId) + '" open>' +
      '<summary class="rc-group-summary"><span class="rc-group-heading"><span class="rc-caret" aria-hidden="true">▸</span><span class="rc-group-title">New group ' + (groupIndex + 1) + '</span><span class="rc-badge rc-enabled-badge">Enabled</span><span class="rc-badge rc-active-badge">Inactive</span><span class="rc-stream-count">0 streams</span></span>' +
      '<span class="rc-group-tools"><input type="button" class="rc-edit-group" value="✏️ Edit" title="Edit this group" aria-label="Edit this group"><input type="button" class="rc-add-stream" value="➕ Add config" title="Add a stream configuration to this group" aria-label="Add a stream configuration to this group"><input type="button" class="rc-remove-group" value="🗑️ Remove" title="Remove this group" aria-label="Remove this group"></span></summary>' +
      '<div class="rc-group-body"><input type="hidden" name="group_id_' + groupIndex + '" value="' + esc(groupId) + '"><div class="rc-group-fields"><label><b>Enabled</b> <input type="checkbox" name="group_enabled_' + groupIndex + '" value="1" checked></label><label><b>Group name</b> <input type="text" name="group_name_' + groupIndex + '" size="30" value=""></label></div>' +
      '<table class="ui_table rc-stream-table"><thead><tr><th>Enabled</th><th>Name</th><th>Protocol</th><th>Stream URL</th><th>Stream key</th><th>Actions</th></tr></thead><tbody></tbody></table></div></details>';
    qs('#rc-groups').insertAdjacentHTML('beforeend', html);
    groupsInput.value = groupIndex + 1;
    addStream(qs('.rc-group[data-group-id="' + groupId + '"]'));
  }
  qsa('.rc-tab').forEach(function(tab) { tab.addEventListener('click', function() { activateTab(tab); }); });
  qs('#rc-add-group').addEventListener('click', addGroup);
  document.addEventListener('click', function(event) {
    var add = event.target.closest('.rc-add-stream');
    if (add) { event.preventDefault(); event.stopPropagation(); addStream(add.closest('.rc-group')); return; }
    var edit = event.target.closest('.rc-edit-group');
    if (edit) { event.preventDefault(); event.stopPropagation(); var group = edit.closest('.rc-group'); group.open = true; var input = qs('input[name^="group_name_"]', group); if (input) input.focus(); return; }
    var removeStream = event.target.closest('.rc-remove-stream');
    if (removeStream) { event.preventDefault(); var row = removeStream.closest('.rc-stream-row'); var group = removeStream.closest('.rc-group'); clearInputs(row); row.parentNode.removeChild(row); updateGroupSummary(group); return; }
    var removeGroup = event.target.closest('.rc-remove-group');
    if (removeGroup) { event.preventDefault(); event.stopPropagation(); var g = removeGroup.closest('.rc-group'); clearInputs(g); g.hidden = true; updateGroupSummary(g); return; }
  });
  document.addEventListener('input', function(event) { var group = event.target.closest && event.target.closest('.rc-group'); if (group) updateGroupSummary(group); });
  document.addEventListener('change', function(event) { var group = event.target.closest && event.target.closest('.rc-group'); if (group) updateGroupSummary(group); });
  qsa('.rc-group').forEach(updateGroupSummary);
})();
</script>
SCRIPT

&ui_print_footer('', '');
