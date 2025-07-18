function initQueryEditor(textareaId, tables) {
  var editor = CodeMirror.fromTextArea(document.getElementById(textareaId), {
    mode: 'text/x-sql',
    lineNumbers: true,
    extraKeys: { 'Ctrl-Space': 'autocomplete' },
    hintOptions: { tables: tables }
  });

  var form = document.getElementById(textareaId).form;
  if (form) {
    form.addEventListener('submit', function () {
      editor.save();
    });
  }
  return editor;
}
