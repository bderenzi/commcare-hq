/* global hqImport, standardHQReport, HQReportDataTables */
define([
    "jquery",
    "hqwebapp/js/initial_page_data",
    "reports/js/filters",
    "reports/js/standard_hq_report",
    "reports/js/config.dataTables.bootstrap",
    "style/js/hq.helpers",
], function(
    $,
    initialPageData,
    filters,
    standardHQReport,
    datatablesConfig
) {
    if (initialPageData.get('renderReportTables')) {
        // TODO: deal with this (breaks because of gettext)
        /*var reportTables = datatablesConfig.HQReportDataTables(initialPageData.get('dataTablesOptions')),
            standardHQReport = standardHQReport.getStandardHQReport();
        if (typeof standardHQReport !== 'undefined') {
            standardHQReport.handleTabularReportCookies(reportTables);
        }
        reportTables.render();*/
    }

    filters.init();

    $(function() {
        $('.header-popover').popover({
            trigger: 'hover',
            placement: 'bottom',
        });
    });
});
