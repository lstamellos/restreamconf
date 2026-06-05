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
    return '<button type="button" class="rc-icon-button ' . &html_escape($class) . '" title="' . &html_escape($title) . '" aria-label="' . &html_escape($title) . '" ' . $attrs . '>' .
        '<span class="rc-icon" aria-hidden="true">' . $icon . '</span><span class="rc-icon-label">' . &html_escape($label) . '</span></button>';
}

sub restreamconf_stream_row_html {
    my ($stream_row, $group_id, $stream, $is_blank) = @_;
    $stream ||= {};
    my $id = $stream->{'id'} || restreamconf_new_id('stream', $stream_row);
    my $row_class = $is_blank ? ' rc-empty-row' : '';
    my $enabled = defined($stream->{'enabled'}) ? $stream->{'enabled'} : 1;
    my $html = '<tr class="rc-stream-row' . $row_class . '" data-row-index="' . int($stream_row) . '">';
    $html .= '<td class="rc-stream-actions">' . &ui_hidden("id_$stream_row", $id) . &ui_hidden("group_$stream_row", $group_id) . &ui_checkbox("enabled_$stream_row", 1, '', $enabled) . '</td>';
    $html .= '<td>' . &ui_textbox("name_$stream_row", $stream->{'name'} || '', 18) . '</td>';
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
.rc-card { background: #fff; border: 1px solid #d7dde8; border-radius: 10px; box-shadow: 0 1px 2px rgba(0,0,0,.04); margin: 1em 0; overflow: hidden; }
.rc-card-body { padding: 1em; }
.rc-intro { color: #56606f; line-height: 1.5; max-width: 920px; }
.rc-tabs { display: flex; flex-wrap: wrap; gap: .4em; border-bottom: 1px solid #d7dde8; margin: 1.25em 0 0; }
.rc-tab { background: #f4f7fb; border: 1px solid #d7dde8; border-bottom: 0; border-radius: 8px 8px 0 0; color: #334155; cursor: pointer; font-weight: 600; padding: .7em 1em; }
.rc-tab[aria-selected="true"] { background: #fff; color: #0f5ca8; position: relative; top: 1px; }
.rc-tab-panel { display: none; }
.rc-tab-panel.rc-active { display: block; }
.rc-section-title { align-items: center; display: flex; gap: .5em; justify-content: space-between; margin: 0 0 .75em; }
.rc-group { border: 1px solid #d7dde8; border-radius: 10px; margin: .9em 0; overflow: hidden; }
.rc-group[hidden] { display: none; }
.rc-group-summary { align-items: center; background: #f8fafc; cursor: pointer; display: flex; gap: .75em; justify-content: space-between; padding: .85em 1em; }
.rc-group-summary:hover { background: #eef5ff; }
.rc-group-heading { align-items: center; display: flex; gap: .65em; min-width: 0; }
.rc-caret { color: #64748b; font-size: 1.15em; }
.rc-group-title { font-size: 1.05em; font-weight: 700; }
.rc-badge { background: #e0f2fe; border-radius: 999px; color: #075985; display: inline-block; font-size: .85em; font-weight: 600; padding: .2em .65em; }
.rc-badge.rc-disabled { background: #fee2e2; color: #991b1b; }
.rc-group-tools, .rc-toolbar, .rc-row-tools { align-items: center; display: flex; flex-wrap: wrap; gap: .4em; }
.rc-group-body { border-top: 1px solid #d7dde8; padding: 1em; }
.rc-group:not([open]) .rc-group-body { display: none; }
.rc-group-fields { align-items: center; background: #fbfdff; border: 1px solid #e5eaf1; border-radius: 8px; display: flex; flex-wrap: wrap; gap: .75em 1.25em; margin-bottom: 1em; padding: .8em; }
.rc-stream-table { border-collapse: collapse; width: 100%; }
.rc-stream-table th { background: #f1f5f9; color: #334155; text-align: left; }
.rc-stream-table th, .rc-stream-table td { border-bottom: 1px solid #e5eaf1; padding: .45em; vertical-align: middle; }
.rc-stream-table input[type="text"] { max-width: 100%; }
.rc-icon-button { align-items: center; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 7px; color: #1f2937; cursor: pointer; display: inline-flex; gap: .35em; line-height: 1.2; padding: .45em .65em; }
.rc-icon-button:hover { background: #eaf4ff; border-color: #93c5fd; color: #0f5ca8; }
.rc-add-group, .rc-add-stream { background: #ecfdf5; border-color: #86efac; color: #166534; }
.rc-remove-group, .rc-remove-stream { background: #fff7ed; border-color: #fdba74; color: #9a3412; }
.rc-monitor-link { font-weight: 600; }
@media (max-width: 760px) { .rc-icon-label { display: none; } .rc-stream-table { display: block; overflow-x: auto; } .rc-tabs { border-bottom: 0; } .rc-tab { border: 1px solid #d7dde8; border-radius: 8px; } }
</style>
STYLE

print &ui_form_start('save.cgi', 'post');
print '<div class="rc-shell">';
print '<p class="rc-intro">Use the tabs below to move between incoming stream settings, destination groups, and monitoring. Groups use accordions so you can focus on one set of outgoing configurations at a time.</p>';

print '<div class="rc-tabs" role="tablist" aria-label="Restream configuration sections">';
print '<button type="button" class="rc-tab" role="tab" aria-selected="true" aria-controls="rc-panel-incoming" id="rc-tab-incoming" data-tab-target="rc-panel-incoming">📥 Incoming</button>';
print '<button type="button" class="rc-tab" role="tab" aria-selected="false" aria-controls="rc-panel-destinations" id="rc-tab-destinations" data-tab-target="rc-panel-destinations">📡 Destinations</button>';
print '<button type="button" class="rc-tab" role="tab" aria-selected="false" aria-controls="rc-panel-monitoring" id="rc-tab-monitoring" data-tab-target="rc-panel-monitoring">📊 Monitoring</button>';
print '</div>';

print '<section class="rc-tab-panel rc-active" role="tabpanel" id="rc-panel-incoming" aria-labelledby="rc-tab-incoming">';
print '<div class="rc-card"><div class="rc-card-body">';
print '<div class="rc-section-title"><h3>📥 Incoming stream</h3></div>';
print &ui_table_start('Incoming stream', undef, 2);
print &ui_table_row('Public RTMP hostname', &ui_textbox('incoming_host', $data->{'incoming_host'} || $config{'incoming_host'} || $DEFAULT_INCOMING_HOST, 32));
print &ui_table_row('Incoming RTMP port', &ui_textbox('incoming_port', $data->{'incoming_port'} || 1935, 8));
print &ui_table_row('Application name', '<code>' . &html_escape($config{'application'} || 'live') . '</code>');
print &ui_table_end();
print '</div></div>';
print '</section>';

print '<section class="rc-tab-panel" role="tabpanel" id="rc-panel-destinations" aria-labelledby="rc-tab-destinations">';
print '<div class="rc-card"><div class="rc-card-body">';
print '<div class="rc-section-title"><h3>📡 Outgoing destinations</h3><div class="rc-toolbar">' . restreamconf_icon_button('rc-add-group', 'Add group', '➕', 'Add a new group', 'id="rc-add-group"') . '</div></div>';
print '<p class="rc-intro">Configure each destination group in its own accordion. A destination only pushes when both its group and its own row are enabled. RTMPS destinations are forwarded through module-owned stunnel4 TLS tunnels, while RTMP destinations are pushed directly by nginx.</p>';
print '<div id="rc-groups">';

my $stream_row = 0;
for (my $group_index = 0; $group_index < $group_rows; $group_index++) {
    my $group = $group_form_rows[$group_index];
    my @group_streams = @{$streams_by_group{$group->{'id'}} || []};
    my $summary_state = $group->{'enabled'} ? 'Enabled' : 'Disabled';
    my $details_attr = ($group_index < @groups || @group_streams) ? ' open' : '';
    my $hidden_attr = (!$group->{'is_existing'} && !@group_streams && $group->{'name'} eq '') ? ' hidden' : '';
    my $stream_count = scalar(@group_streams);
    my $title = $group->{'name'} || 'New group ' . ($group_index + 1);

    print '<details class="rc-group" data-group-index="' . int($group_index) . '" data-group-id="' . &html_escape($group->{'id'}) . '"' . $details_attr . $hidden_attr . '>';
    print '<summary class="rc-group-summary">';
    print '<span class="rc-group-heading"><span class="rc-caret" aria-hidden="true">▸</span><span class="rc-group-title">' . &html_escape($title) . '</span><span class="rc-badge' . ($group->{'enabled'} ? '' : ' rc-disabled') . '">' . $summary_state . '</span><span class="rc-stream-count">' . int($stream_count) . ' stream' . ($stream_count == 1 ? '' : 's') . '</span></span>';
    print '<span class="rc-group-tools">' . restreamconf_icon_button('rc-edit-group', 'Edit', '✏️', 'Edit this group') . restreamconf_icon_button('rc-add-stream', 'Add config', '➕', 'Add a stream configuration to this group') . restreamconf_icon_button('rc-remove-group', 'Remove', '🗑️', 'Remove this group') . '</span>';
    print '</summary>';
    print '<div class="rc-group-body">';
    print &ui_hidden("group_id_$group_index", $group->{'id'});
    print '<div class="rc-group-fields">';
    print '<label><b>Enabled</b> ' . &ui_checkbox("group_enabled_$group_index", 1, '', $group->{'enabled'}) . '</label>';
    print '<label><b>Group name</b> ' . &ui_textbox("group_name_$group_index", $group->{'name'}, 30) . '</label>';
    print '</div>';
    print '<table class="rc-stream-table"><thead><tr><th>Enabled</th><th>Name</th><th>Protocol</th><th>Stream URL</th><th>Stream key</th><th>Actions</th></tr></thead><tbody>';
    foreach my $stream (@group_streams) {
        print restreamconf_stream_row_html($stream_row, $group->{'id'}, $stream, 0);
        $stream_row++;
    }
    print restreamconf_stream_row_html($stream_row, $group->{'id'}, {}, 1);
    $stream_row++;
    print '</tbody></table>';
    print '</div></details>';
}
print '</div>';
print &ui_hidden('group_rows', $group_rows);
print &ui_hidden('rows', $stream_row);
print '</div></div>';
print '</section>';

print '<section class="rc-tab-panel" role="tabpanel" id="rc-panel-monitoring" aria-labelledby="rc-tab-monitoring">';
print '<div class="rc-card"><div class="rc-card-body">';
print '<div class="rc-section-title"><h3>📊 Monitoring</h3></div>';
print restreamconf_render_status_table($data);
print '<p><a class="rc-monitor-link" href="dashboard.cgi">Open standalone monitoring view</a>. Diagnostics include nginx config/include checks, listener PIDs, generated stunnel4 actions, and tunnel ports.</p>';
print '</div></div>';
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
  function updateGroupSummary(group) {
    var nameInput = qs('input[name^="group_name_"]', group);
    var enabledInput = qs('input[name^="group_enabled_"]', group);
    var title = qs('.rc-group-title', group);
    var badge = qs('.rc-badge', group);
    var count = qsa('.rc-stream-row', group).filter(function(row) {
      var name = qs('input[name^="name_"]', row);
      var url = qs('input[name^="url_"]', row);
      var key = qs('input[name^="key_"]', row);
      return (name && name.value.trim()) || (url && url.value.trim()) || (key && key.value.trim());
    }).length;
    if (title && nameInput) title.textContent = nameInput.value.trim() || 'New group ' + (Number(group.getAttribute('data-group-index')) + 1);
    if (badge && enabledInput) {
      badge.textContent = enabledInput.checked ? 'Enabled' : 'Disabled';
      badge.classList.toggle('rc-disabled', !enabledInput.checked);
    }
    var countEl = qs('.rc-stream-count', group);
    if (countEl) countEl.textContent = count + ' stream' + (count === 1 ? '' : 's');
  }
  function streamRowHtml(rowIndex, groupId) {
    var safeGroup = esc(groupId);
    return '<tr class="rc-stream-row rc-empty-row" data-row-index="' + rowIndex + '">' +
      '<td class="rc-stream-actions"><input type="hidden" name="id_' + rowIndex + '" value="stream_' + Date.now() + '_' + rowIndex + '"><input type="hidden" name="group_' + rowIndex + '" value="' + safeGroup + '"><input type="checkbox" name="enabled_' + rowIndex + '" value="1" checked></td>' +
      '<td><input type="text" name="name_' + rowIndex + '" size="18" value=""></td>' +
      '<td><select name="protocol_' + rowIndex + '"><option value="rtmp" selected>RTMP</option><option value="rtmps">RTMPS</option></select></td>' +
      '<td><input type="text" name="url_' + rowIndex + '" size="45" value=""></td>' +
      '<td><input type="text" name="key_' + rowIndex + '" size="24" value=""></td>' +
      '<td class="rc-row-tools"><button type="button" class="rc-icon-button rc-remove-stream" title="Remove this configuration" aria-label="Remove this configuration"><span class="rc-icon" aria-hidden="true">🗑️</span><span class="rc-icon-label">Remove</span></button></td>' +
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
    var html = '<details class="rc-group" data-group-index="' + groupIndex + '" data-group-id="' + esc(groupId) + '" open>' +
      '<summary class="rc-group-summary"><span class="rc-group-heading"><span class="rc-caret" aria-hidden="true">▸</span><span class="rc-group-title">New group ' + (groupIndex + 1) + '</span><span class="rc-badge">Enabled</span><span class="rc-stream-count">0 streams</span></span>' +
      '<span class="rc-group-tools"><button type="button" class="rc-icon-button rc-edit-group" title="Edit this group" aria-label="Edit this group"><span class="rc-icon" aria-hidden="true">✏️</span><span class="rc-icon-label">Edit</span></button><button type="button" class="rc-icon-button rc-add-stream" title="Add a stream configuration to this group" aria-label="Add a stream configuration to this group"><span class="rc-icon" aria-hidden="true">➕</span><span class="rc-icon-label">Add config</span></button><button type="button" class="rc-icon-button rc-remove-group" title="Remove this group" aria-label="Remove this group"><span class="rc-icon" aria-hidden="true">🗑️</span><span class="rc-icon-label">Remove</span></button></span></summary>' +
      '<div class="rc-group-body"><input type="hidden" name="group_id_' + groupIndex + '" value="' + esc(groupId) + '"><div class="rc-group-fields"><label><b>Enabled</b> <input type="checkbox" name="group_enabled_' + groupIndex + '" value="1" checked></label><label><b>Group name</b> <input type="text" name="group_name_' + groupIndex + '" size="30" value=""></label></div>' +
      '<table class="rc-stream-table"><thead><tr><th>Enabled</th><th>Name</th><th>Protocol</th><th>Stream URL</th><th>Stream key</th><th>Actions</th></tr></thead><tbody></tbody></table></div></details>';
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
