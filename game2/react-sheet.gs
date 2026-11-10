/**
 * Random Walk 엔딩 반응(❤️ 👍 💪) 저장용 Google Apps Script
 *
 * 1) 새 구글 시트를 만든다.
 * 2) 확장 프로그램 → Apps Script → 이 코드를 통째로 붙여넣고 저장.
 * 3) 배포 → 새 배포 → 유형: 웹 앱
 *      실행 사용자: 나 / 액세스 권한: 모든 사용자
 * 4) 나온 웹 앱 URL(https://script.google.com/macros/s/.../exec)을
 *    game2/index.html 의 const REACT_URL='' 안에 넣는다.
 *
 * 시트에는 시각과 버튼 종류만 한 줄씩 쌓여요. 이름·기기 정보는 받지 않아요(익명).
 */
const KINDS = ['heart', 'thumb', 'muscle'];

function doGet(e) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  const p = (e && e.parameter) || {};
  if (p.op === 'add' && KINDS.indexOf(p.k) >= 0) {
    sheet.appendRow([new Date(), p.k]);
  }
  const counts = { heart: 0, thumb: 0, muscle: 0 };
  const last = sheet.getLastRow();
  if (last > 0) {
    sheet.getRange(1, 2, last, 1).getValues().forEach(function (r) {
      if (counts.hasOwnProperty(r[0])) counts[r[0]]++;
    });
  }
  return ContentService.createTextOutput(JSON.stringify(counts))
    .setMimeType(ContentService.MimeType.JSON);
}
