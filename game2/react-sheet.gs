const KINDS = ['heart', 'thumb', 'muscle'];
function getSheet() {
  const props = PropertiesService.getScriptProperties();
  let id = props.getProperty('SHEET_ID');
  if (!id) {
    id = SpreadsheetApp.create('Random Walk 반응').getId();
    props.setProperty('SHEET_ID', id);
  }
  const sh = SpreadsheetApp.openById(id).getSheets()[0];
  if (sh.getLastRow() === 0) sh.appendRow(['시각', '방문자', '이벤트', '내용', '언어', '기기']);
  return sh;
}
function cut(x, n) { return String(x || '').slice(0, n); }
function doGet(e) {
  const sh = getSheet();
  const p = (e && e.parameter) || {};
  if (p.op === 'add' && KINDS.indexOf(p.k) >= 0) {
    sh.appendRow([new Date(), cut(p.v, 10), 'react', p.k, cut(p.l, 4), cut(p.d, 20)]);
  } else if (p.op === 'log') {
    sh.appendRow([new Date(), cut(p.v, 10), cut(p.ev, 30), cut(p.k, 60), cut(p.l, 4), cut(p.d, 20)]);
  }
  const counts = { heart: 0, thumb: 0, muscle: 0 };
  const last = sh.getLastRow();
  if (last > 0) sh.getRange(1, 1, last, 4).getValues().forEach(function (r) {
    if (r[2] === 'react' && counts.hasOwnProperty(r[3])) counts[r[3]]++;
    else if (counts.hasOwnProperty(r[1])) counts[r[1]]++;
  });
  return ContentService.createTextOutput(JSON.stringify(counts))
    .setMimeType(ContentService.MimeType.JSON);
}
