export function createDataTable(selector) {
  return $(selector).DataTable({
    ordering: false,
    pageLength: 20,
    lengthChange: false,
    pagingType: 'full_numbers',
    stateSave: true,
  });
}
