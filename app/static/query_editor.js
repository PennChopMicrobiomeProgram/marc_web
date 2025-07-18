function initQueryEditor(containerId, hiddenInputId, tables) {
  const input = document.getElementById(hiddenInputId);
  const editor = CodeMirror(document.getElementById(containerId), {
    value: input.value || "",
    mode: "text/x-sql",
    lineNumbers: true,
    extraKeys: { "Ctrl-Space": "autocomplete" },
    hintOptions: { tables: tables },
  });

  editor.on("inputRead", function (cm, change) {
    if (change.origin !== "setValue") {
      CodeMirror.commands.autocomplete(cm, null, { completeSingle: false });
    }
  });

  editor.on("change", function (cm) {
    input.value = cm.getValue();
  });

  const form = input.form;
  if (form) {
    form.addEventListener("submit", function () {
      input.value = editor.getValue();
    });
  }
  return editor;
}
