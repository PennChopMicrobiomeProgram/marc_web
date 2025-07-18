function initQueryEditor(containerId, hiddenInputId, tables) {
  const input = document.getElementById(hiddenInputId);
  const keywords = [];
  for (const [table, fields] of Object.entries(tables || {})) {
    keywords.push(table);
    for (const f of fields) {
      keywords.push(f);
    }
  }
  const editor = CodeMirror(document.getElementById(containerId), {
    value: input.value || "",
    mode: "text/x-sql",
    lineNumbers: true,
    extraKeys: { "Ctrl-Space": "autocomplete" },
    hintOptions: { tables: tables, keywords: keywords },
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
