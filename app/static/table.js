function createDataTable(selector) {
  return $(selector).DataTable({
    ordering: false,
    pageLength: 20,
    lengthChange: false,
    pagingType: 'full_numbers',
    stateSave: true,
  });
}

function createServerDataTable(selector, ajaxUrl, columns) {
  return $(selector).DataTable({
    serverSide: true,
    processing: true,
    ajax: ajaxUrl,
    columns: columns,
    pageLength: 20,
    lengthChange: false,
    pagingType: 'full_numbers',
    stateSave: true,
  });
}
