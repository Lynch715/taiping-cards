/** Keep historical prose untouched; only combat labels use the army vocabulary. */
export const militaryText=(text='')=>text.replace(/生命值?|血量/g,'兵力').replace(/自身阵亡/g,'自身部队溃散').replace(/友方阵亡/g,'友军溃散').replace(/阵亡/g,'部队溃散');
