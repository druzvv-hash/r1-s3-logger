// Factory-interface workbooks from freshly extracted frozen-board inventory.
import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile,FileBlob} from '@oai/artifact-tool';
const dir=path.resolve(process.argv[2]);
const data=JSON.parse(await fs.readFile(path.join(dir,'assembly_source.json'),'utf8'));
const results=[];
for(const [name,matrix] of Object.entries(data.tables)){
 const wb=Workbook.create(),sh=wb.worksheets.add(name);
 const range=sh.getRangeByIndexes(0,0,matrix.length,matrix[0].length);
 range.values=matrix;range.format.font={name:'Arial',size:10};
 sh.showGridLines=false;sh.freezePanes.freezeRows(1);
 range.format.rowHeight=18;range.format.columnWidth=23;
 sh.getRangeByIndexes(0,0,1,matrix[0].length).format={fill:'#24445c',font:{name:'Arial',size:10,bold:true,color:'#ffffff'}};
 for(let i=0;i<matrix[0].length;i++){
   const header=matrix[0][i];sh.getRangeByIndexes(0,i,matrix.length,1).format.columnWidth=header==='Footprint'?58:['Value','Comment'].includes(header)?43:header==='Designator'?14:24;
   if(['Mid X','Mid Y','Rotation'].includes(header))sh.getRangeByIndexes(1,i,matrix.length-1,1).setNumberFormat('0.000000');
 }
 wb.recalculate();
 if(JSON.stringify(range.values)!==JSON.stringify(matrix))throw Error(name+' values mismatch');
 const filename=path.join(dir,'R3_RevA_'+name+'.xlsx');
 await (await SpreadsheetFile.exportXlsx(wb)).save(filename);
 const reopened=await SpreadsheetFile.importXlsx(await FileBlob.load(filename));
 const values=reopened.worksheets.getItemAt(0).getRangeByIndexes(0,0,matrix.length,matrix[0].length).values;
 if(JSON.stringify(values)!==JSON.stringify(matrix))throw Error(name+' saved values mismatch');
 const png=await wb.render({sheetName:name,range:`A1:${String.fromCharCode(64+matrix[0].length)}7`,scale:1,format:'png'});
 await fs.writeFile(path.join(dir,name+'_preview.png'),new Uint8Array(await png.arrayBuffer()));
 results.push({file:path.basename(filename),rows:matrix.length-1,pass:true,fields:matrix[0]});
}
// Reconcile independently by stable reference, not row ordering.
for(const label of ['A_TOP','B_BOTH']){
 const bom=data.tables[label+'_BOM'].slice(1),cpl=data.tables[label+'_CPL'].slice(1);
 const byRef=new Map(data.inventory.map(r=>[r.ref,r]));
 if(new Set(bom.map(r=>r[1])).size!==bom.length||new Set(cpl.map(r=>r[0])).size!==cpl.length)throw Error('duplicate RefDes');
 if(bom.length!==cpl.length)throw Error('BOM CPL count');
 for(const row of cpl){
  const r=byRef.get(row[0]),b=bom.find(v=>v[1]===r.ref);
  if(!b||r.disposition!=='FACTORY_CANDIDATE')throw Error('excluded ref');
  if(JSON.stringify(row)!==JSON.stringify([r.ref,r.x,r.y,r.side,r.rotation,r.footprint,r.mpn,r.lcsc]))throw Error('CPL parity');
  if(b[2]!==r.footprint||b[3]!==r.lcsc||b[4]!==r.mpn||b[6]!==r.side)throw Error('BOM parity');
  if(label==='A_TOP'&&r.side!=='Top')throw Error('Bottom in A');
 }
}
await fs.writeFile(path.join(dir,'assembly_file_validation.json'),JSON.stringify({pass:true,source_commit:data.source_commit,pcb_sha256:data.pcb_sha256,results,scope:'RefDes, side, X/Y, native rotation, footprint, MPN and LCSC exactly match frozen inventory; UNRESOLVED is preserved, not procurement acceptance.'},null,2));
console.log(JSON.stringify(results));
