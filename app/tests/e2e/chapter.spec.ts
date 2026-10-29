/** Reproduction smoke test. Actual acceptance runs use the in-app browser. */
import { test,expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { database } from '../../src/core/data';
const difficulty=JSON.parse(readFileSync('../assets/reports/m1/chapter1/difficulty.json','utf8')) as {stages:{stage_id:string;formation:string[]}[]};
for(const camp of ['taiping','qing'])test(`${camp}: complete6stages and restore progress`,async({page})=>{
 await page.goto(`/?qa=e2e-${camp}`);await page.getByRole('button',{name:camp==='taiping'?/执掌太平军/:/执掌清军/}).click();
 const stages=database.stages.filter(x=>x.campaign===camp&&x.chapter===1).sort((a,b)=>a.order-b.order);
 for(const stage of stages){
  const team=difficulty.stages.find(x=>x.stage_id===stage.stage_id)!.formation;
  for(const [i,id]of team.entries()){const name=database.heroes.find(h=>h.id===id)!.name;await page.getByRole('button',{name:new RegExp(`调整${i<2?'前排':'后排'}第${i<2?i+1:i-1}位`)}).click();await page.locator('.roster-grid').getByRole('button',{name:new RegExp(`^${name}`)}).click();}
  for(let retry=0;retry<20;retry++){
   await page.getByRole('button',{name:/出征/}).click();await expect(page.getByTestId('battle-scene')).toHaveAttribute('aria-busy','false');await page.getByRole('button',{name:'跳过',exact:true}).click();
   if(await page.getByRole('heading',{name:'军势大振'}).isVisible())break;
   await page.getByRole('button',{name:'返回编队',exact:true}).click();
  }
  await expect(page.getByRole('heading',{name:'军势大振'})).toBeVisible();
  if(stage.order<6)await page.getByRole('button',{name:'下一关',exact:true}).click();
 }
 await page.reload();await expect(page.getByText('6 / 6 捷',{exact:false})).toBeVisible();
});
