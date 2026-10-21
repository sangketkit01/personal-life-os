# Portfolio UX/UI audit — 21 October 2026

ตรวจจาก Vue components, Pinia store, API views, serializers และ calculation service เท่านั้น รายงานนี้ไม่ได้ยืนยัน layout ด้วยการ render และไม่ได้แก้ application logic

P1 = กระทบความถูกต้องของข้อมูล/บริบทหรือทำให้บันทึกผิดได้ ควรแก้ก่อนปรับหน้าตา; P2 = ทำให้ workflow สับสน ใช้งานสะดุด หรือให้ feedback ผิด

## ข้อค้นพบจากโค้ด

### F01 · P1 · หน้ารายละเอียดเปลี่ยนสัญลักษณ์เงินโดยไม่เปลี่ยนค่าตัวเลข

- หลักฐาน: `frontend/src/views/StockDetailView.vue:157`, `:166`, `:178`, `:584`; `backend/apps/portfolio/services.py:166`
- หน้ารายละเอียดใช้ `currSymbol` จาก display currency แต่แสดง `position.market_value`, `total_invested`, `unrealized_pnl`, `total_realized_pnl` ซึ่งเป็นสกุลของ holding
- ตัวอย่าง: holding USD มี market value 100 แต่เลือก THB หน้ารายละเอียดแสดง ฿100 แทนค่าที่แปลงแล้ว ขณะที่กราฟและ avg cost ยังใช้สกุลเดิม ทำให้ตัวเลขในหน้าเดียวกันตีความไม่ตรงกัน
- แก้: ใช้ field `_thb`/`_usd` ตามสกุลที่แสดง หรือใช้ native currency ทั้งหน้า พร้อมระบุชัดว่าเป็นสกุลใด
- เกณฑ์ผ่าน: เปิด holding USD ในมุมมอง THB แล้วมูลค่าและ P&L ตรงกับแถวในหน้ารวมทุกช่อง

### F02 · P1 · Refresh ทำให้ยอดสรุปหลุดจากพอร์ตและ asset class ที่เลือก

- หลักฐาน: `frontend/src/stores/portfolio.ts:320`; `backend/apps/portfolio/views.py:102`
- store ส่งเพียง `{ force }` ให้ refresh API แล้วแทนที่ overview แต่ backend ต้องได้รับ portfolio_id/asset_type เพื่อคง scope ส่วน fetchHoldings ที่เรียกต่อยังใช้ตัวกรองปัจจุบัน
- ผล: เลือกพอร์ต A หรือ Crypto แล้ว refresh/รอ polling ยอดด้านบนกลับเป็นทุกพอร์ต แต่ตารางยังเป็นรายการที่เลือก
- แก้: ส่ง scope เดียวกันทุก request และรับผลเฉพาะเมื่อ scope ยังตรงกับหน้าปัจจุบัน
- เกณฑ์ผ่าน: manual refresh และ polling ไม่เปลี่ยนผลรวมจากชุดสินทรัพย์ที่เลือก; สลับตัวกรองเร็วแล้ว response เก่าไม่ทับชุดใหม่

### F03 · P1 · Trade Currency เปลี่ยนความหมายของ holding ทั้งก้อน

- หลักฐาน: `frontend/src/components/portfolio/AddTransactionModal.vue:249`, `:517`; `backend/apps/portfolio/serializers.py:177`, `:218`; `backend/apps/portfolio/services.py:186`
- เลือก verified asset แล้วผู้ใช้เปลี่ยน Trade Currency ได้ แต่ backend เปลี่ยน holding.currency ตาม transaction ขณะที่ calculation รวมตัวเลขของ transactions โดยไม่แปลงตาม tx.currency
- ผล: การบันทึกรายการเดียวต่างสกุลอาจทำให้ต้นทุนเดิมทั้งหมดถูกตีความเป็นสกุลใหม่ และ snapshot ราคายังเป็นสกุลตลาดเดิม
- แก้: แยก quote currency, transaction currency และ display currency; ถ้ารองรับการจ่ายต่างสกุลต้องมี FX และจำนวนเงินที่แปลงอย่างชัดเจน มิฉะนั้นให้ล็อกสกุลของสินทรัพย์
- เกณฑ์ผ่าน: บันทึก trade ใหม่ไม่เปลี่ยน denomination ของประวัติเดิมโดยเงียบ ๆ

### F04 · P1 · หน้ารายละเอียดไม่ระบุว่าเป็น holding ของพอร์ตใด

- หลักฐาน: `frontend/src/views/PortfolioView.vue:1189`; `backend/apps/portfolio/views.py:198`; `frontend/src/views/StockDetailView.vue:734`; `frontend/src/stores/portfolio.ts:186`
- route ส่งเพียง ticker; backend เลือก holding ตัวแรกของ ticker นั้นข้ามทุกพอร์ต ส่วนประวัติ transaction ใช้ selectedPortfolioId ที่ค้างอยู่ใน store
- ผล: ถือ AAPL ในพอร์ต A และ B แล้วเปิดจาก B อาจได้ยอดและปุ่ม trade/move ของ A แต่ history ของ B; ใน All Portfolios ได้ยอด holding เดียวกับ history หลายพอร์ต
- แก้: route สำหรับ holding ต้องมี holdingId หรือ portfolioId+ticker; หน้า market asset ที่รวมหลายพอร์ตควรแสดง aggregate และเลือกพอร์ตก่อนทำรายการ
- เกณฑ์ผ่าน: ticker เดียวกันสองพอร์ตเปิดรายละเอียดได้ยอด ประวัติ และ action ของพอร์ตเดียวกันเสมอ

### F05 · P1 · เปลี่ยน Target Portfolio ใน trade ที่เปิดจาก holding แล้วอาจไม่มีผล

- หลักฐาน: `frontend/src/components/portfolio/AddTransactionModal.vue:74`, `:702`, `:708`; `backend/apps/portfolio/serializers.py:119`, `:137`
- dropdown ยังเปลี่ยนพอร์ตได้สำหรับ new trade แม้มี prefillHoldingId แต่ payload ส่งทั้ง holding และ portfolio; backend ใช้ portfolio หา holding เฉพาะเมื่อยังไม่มี holding เท่านั้น
- ผล: UI บอกว่าเลือกพอร์ต B แต่ trade ถูกผูกกับ holding เดิมใน A
- แก้: ล็อก target portfolio เมื่อผูก holding หรือ resolve holding ใหม่ให้ตรงกับพอร์ตที่เลือก; currentHolding/Max Sell ต้องค้นด้วยพอร์ตและ ticker คู่กัน
- เกณฑ์ผ่าน: พอร์ตใน confirmation summary ตรงกับเจ้าของ transaction ที่บันทึกจริง

### F06 · P1 · บันทึกสำเร็จแต่ UI แจ้งล้มเหลว และเสี่ยงบันทึกซ้ำ

- หลักฐาน: `frontend/src/stores/portfolio.ts:336`; `frontend/src/components/portfolio/AddTransactionModal.vue:383`, `:664`
- หลัง POST สำเร็จ store รอ overview, holdings, transactions และ news ใน Promise.all; GET ใดล้มเหลวจะโยน error เหมือน POST ล้มเหลว และ modal ยังเปิดอยู่
- isLoading ร่วมยังถูก fetchHoldings ตั้งเป็น false ได้ก่อนขั้นตอนอื่นจบ ทำให้สถานะ Posting ไม่ครอบคลุม transaction ทั้งชุด
- แก้: แยก mutation state กับ refresh state; POST สำเร็จต้องแจ้งว่าบันทึกแล้ว ส่วนส่วนแสดงผลที่โหลดไม่สำเร็จให้ retry เฉพาะการโหลด เพิ่มการป้องกันคำขอบันทึกซ้ำที่ server
- เกณฑ์ผ่าน: จำลอง news GET ล้มเหลวหลัง POST สำเร็จ ผู้ใช้เห็นว่าบันทึกแล้วและไม่มีการเสนอให้ส่ง trade ซ้ำ

### F07 · P1 · เปิดแก้ transaction แล้วเวลาถอยหลังตาม timezone

- หลักฐาน: `frontend/src/components/portfolio/AddTransactionModal.vue:614`, `:697`
- edit ใช้ toISOString().slice(0,16) ซึ่งเป็น UTC ใส่ datetime-local แต่ submit ตีความค่านั้นเป็นเวลาท้องถิ่น
- ตัวอย่าง: รายการ 10:00 ที่ Bangkok เปิดแก้จะกลายเป็น 03:00 และกดบันทึกโดยไม่แตะเวลาก็เลื่อน transaction ไป 7 ชั่วโมง อาจเปลี่ยนลำดับคำนวณต้นทุน
- แก้: ใช้ local datetime conversion แบบเดียวกับ getNowLocalDateTime; ระบุ timezone ข้างช่อง
- เกณฑ์ผ่าน: เปิดและบันทึกโดยไม่เปลี่ยนเวลา ต้องได้ timestamp เดิม รวมกรณีใกล้เที่ยงคืน

### F08 · P1 · Sell ผ่าน ticker อาจข้ามการตรวจจำนวนที่ขายได้

- หลักฐาน: `frontend/src/components/portfolio/AddTransactionModal.vue:499`, `:686`; `backend/apps/portfolio/serializers.py:106`, `:137`; `backend/apps/portfolio/services.py:194`
- frontend ตรวจเทียบ currentHolding ที่อยู่ใน store ซึ่งอาจไม่มีหรือเป็นคนละพอร์ต; backend validate SELL เฉพาะเมื่อ attrs มี holding แต่การส่ง ticker จะ resolve holding ภายหลังใน create
- calculation ใช้ min(tx.shares, total_shares) จึงอาจมี trade บันทึกว่า sell มากกว่าที่ถือ แต่ position คำนวณจากจำนวนที่ต่ำกว่า
- แก้: resolve holding ก่อน validate; ตรวจ sequence ทั้งชุดหลัง create/edit/delete รวมวันที่ย้อนหลัง แล้วคืน error ตรงช่อง shares
- เกณฑ์ผ่าน: ทั้งการเปิดจากแถวและ Record Trade กลางปฏิเสธ oversell เหมือนกัน; ประวัติและ position ใช้จำนวนเดียวกัน

### F09 · P2 · Buy จาก Watchlist ไม่พร้อมทำรายการสินทรัพย์ที่กดมา

- หลักฐาน: `frontend/src/views/PortfolioView.vue:1475`; `frontend/src/components/portfolio/AddTransactionModal.vue:481`, `:597`, `:618`
- ส่ง prefillTicker แต่ modal ล้าง selectedAsset/searchQuery และ isSubmitDisabled บังคับเลือก verified asset ใหม่
- ผล: กด Buy ของสินทรัพย์ที่เห็นอยู่แล้วกลับได้ช่องค้นหาว่างและ Save ปิด ต้องค้นซ้ำ
- แก้: resolve prefillTicker เป็น verified asset ก่อนเปิดฟอร์ม หรือแสดงสถานะกำลังตรวจสอบโดยคงชื่อสินทรัพย์
- เกณฑ์ผ่าน: Buy จาก Watchlist/หน้า research คง ticker และพอร์ตให้ครบ เติมจำนวนกับราคาแล้วบันทึกได้

### F10 · P2 · ปุ่มเพิ่ม Watchlist อาจลบรายการ แต่แจ้งว่าเพิ่มสำเร็จ

- หลักฐาน: `frontend/src/views/PortfolioView.vue:1451`; `backend/apps/portfolio/views.py:597`
- Quick Add เรียก toggle และไม่ใช้ค่าบูลีนที่คืนกลับ ถ้า ticker มีอยู่แล้ว endpoint จะลบออก แต่ toast ยังบอกว่าเพิ่มแล้ว
- แก้: ใช้ create ที่เพิ่มซ้ำแล้วคงสถานะเดิม หรือแสดง Already in Watchlist; ปุ่ม remove ใช้ delete ชัดเจน
- เกณฑ์ผ่าน: กดเพิ่ม ticker เดิมสองครั้ง รายการยังอยู่และข้อความตรงกับผลจริง

### F11 · P2 · ตัวกรองข่าว Watchlist ไม่มีผล

- หลักฐาน: `frontend/src/views/PortfolioView.vue:1518`; `frontend/src/stores/portfolio.ts:223`; `backend/apps/portfolio/views.py:496`
- view ใส่ watchlist_only ใน params แต่ fetchNews ไม่ประกาศหรือส่ง field นี้ต่อ แม้ backend รองรับ
- ผล: tab แสดงบริบท Watchlist แต่ข้อมูลเป็นข่าวจาก scope กว้างกว่า
- แก้: เพิ่ม typed option watchlist_only และส่งให้ API; คง scope หลัง sync และหลังบันทึก trade ซึ่งปัจจุบัน fetchNews แบบไม่มี filters
- เกณฑ์ผ่าน: ticker ข่าวทุกชิ้นอยู่ใน watchlist เมื่อเลือก scope นี้ และยังคงเดิมหลัง refresh

### F12 · P2 · ยอดเงินใน Executions ไม่ตรงกับฟอร์มสำหรับ Sell/Dividend

- หลักฐาน: `frontend/src/views/PortfolioView.vue:1077`; `frontend/src/components/portfolio/AddTransactionModal.vue:646`; `frontend/src/views/StockDetailView.vue:351`
- feed หน้ารวมบวก fee ทุก transaction แต่ modal และหน้ารายละเอียดหัก fee สำหรับ SELL/DIVIDEND
- ตัวอย่าง: ขาย 10 × 100 ค่าธรรมเนียม 5 modal แสดง 995 แต่ feed แสดง 1,005
- แก้: ใช้ formatter/calculation helper เดียวกัน แสดงยอดจ่าย/ยอดรับสุทธิและ fee แยกกัน รวม label ภาษาที่ตรงกัน
- เกณฑ์ผ่าน: confirmation, executions feed และ asset history แสดง net amount ตรงกันทั้งสามประเภท

### F13 · P2 · ข้อความ Synced/Live ไม่ยืนยันความสดของราคา

- หลักฐาน: `frontend/src/stores/portfolio.ts:325`; `frontend/src/views/PortfolioView.vue:201`, `:1351`; `backend/apps/portfolio/services.py:68`, `:224`
- API ใช้ cached snapshot เมื่อดึงราคาสดไม่สำเร็จ แต่ frontend ตั้ง Synced เป็นเวลาปัจจุบัน ส่วน Live อิงสถานะตลาด ไม่ได้อิงผลการโหลด; เมื่อไม่มี quote calculation ใช้ avg cost เป็น current price โดยไม่แสดง provenance
- ผล: ข้อมูลเก่าดูเหมือนสด หรือไม่มีราคาจริงแต่เห็น Unrealized P&L 0; ถ้า initial Promise.all ล้มเหลว polling ยังไม่ได้ถูกตั้งขึ้น
- แก้: ส่ง quote timestamp, source/freshness และ failed tickers; แยก Live/Delayed/Stale/Unavailable ตามข้อมูลจริง และแสดง unavailable แทนราคาที่ไม่รู้
- เกณฑ์ผ่าน: provider ล่มหรือไม่มี snapshot ต้องเห็นสถานะที่อธิบายได้ และไม่ใช้เวลาที่ request จบแทนเวลาราคา

### F14 · P2 · กราฟแสดง series เก่าภายใต้ timeframe ใหม่ได้

- หลักฐาน: `frontend/src/components/portfolio/StockPriceChart.vue:64`, `:406`
- เปลี่ยน selectedPeriod ก่อน fetch; ถ้า fetch ล้มเหลว catch เพียง log และยังเก็บ chartData เก่า อีกทั้ง response ไม่มี guard จึงทับกันได้เมื่อสลับ timeframe เร็ว
- empty state ยังกล่าวว่า sync ทำงานปกติแม้ไม่มีหลักฐานยืนยัน และ chart ไม่ reload เมื่อ currentPrice เปลี่ยนจาก Sync Market Data
- แก้: เก็บ request key ตาม ticker+period, รับเฉพาะ response ปัจจุบัน และแสดง error/retry พร้อม period ของข้อมูลจริง; reload chart เมื่อ sync เสร็จ
- เกณฑ์ผ่าน: สลับ 1D → 1Y แล้ว request 1Y ล้มเหลวต้องไม่เห็นข้อมูล 1D พร้อมป้าย 1Y

### F15 · P2 · ย้ายแล้ว merge สำเร็จ แต่ Save Settings อาจแจ้งล้มเหลว

- หลักฐาน: `frontend/src/components/portfolio/EditHoldingModal.vue:196`; `backend/apps/portfolio/views.py:405`
- EditHolding เรียก move ก่อน update; ถ้าปลายทางมี ticker เดียวกัน backend merge และลบ source holding แล้ว component ยัง PATCH source id เดิม
- ผล: พอร์ตเปลี่ยนไปแล้ว แต่ modal แจ้ง Failed to update asset settings และ metadata ที่แก้ไม่ถูกบันทึก
- แก้: ใช้ holding id ที่ move คืนมา หรือทำ atomic endpoint; preview ให้รู้ก่อนว่าการย้ายจะ merge ประวัติทั้งหมด
- เกณฑ์ผ่าน: ย้ายไปยังพอร์ตที่มี ticker เดิมพร้อมแก้ notes สำเร็จครบ หรือ rollback ทั้งชุด

### F16 · P2 · Realized PnL อธิบายว่าเป็น closed profit/loss แต่รวมเงินปันผล

- หลักฐาน: `backend/apps/portfolio/services.py:213`; `frontend/src/views/PortfolioView.vue:278`, `:294`
- service บวก net dividend เข้า total_realized_pnl แต่หน้ารวมเรียก CLOSED/Cumulative closed profit/loss และมี Dividends แยกอีกการ์ด
- ผล: ผู้ใช้อาจเข้าใจว่า Realized มาจากการขายเท่านั้น หรือบวก Realized กับ Dividends แล้วนับเงินปันผลซ้ำ
- แก้: แยก Realized from sales / Net dividends / Total realized income หรือระบุอย่างตรงไปตรงมาว่า Realized includes dividends
- เกณฑ์ผ่าน: holding ที่ซื้อแล้วรับปันผลอย่างเดียว ต้องไม่ถูกอธิบายว่าเกิดกำไรจาก closed position

## การจัดหน้าและ interaction ที่แนะนำ

ข้อเสนอส่วนนี้เป็นการประเมินจากโครงสร้าง template/CSS ไม่ใช่ผลทดสอบ viewport หรือ contrast ที่ render จริง

1. **รวมบริบทไว้แถบเดียว:** Portfolio selector → display currency → data freshness; ตอนนี้มี currency toggle ทั้ง header และ command strip รวมถึงคำว่า currency ใน portfolio/holding/trade ที่หมายถึงคนละอย่าง (`PortfolioView.vue:16`, `:129`)
2. **ให้ Holdings อยู่ใกล้ยอดสรุป:** ปัจจุบัน allocation อยู่ก่อน tab ทั้งหมด จึงดันงานหลักลงล่างแม้ผู้ใช้สนใจ Watchlist หรือ Executions; ย้าย allocation ไป Overview หรือทำ panel ย่อ โดยเฉพาะเมื่อมี asset class เดียว (`:317`, `:322`)
3. **ลดภาระของตาราง:** ค่าเริ่มต้นให้เห็น Asset, Value, Unrealized P&L, Shares และราคา; advanced columns เช่น Avg Cost/Realized/Denom เลือกเปิดได้ รวม Edit/Move/Delete ในเมนูต่อแถว แล้วคง View และ Record Trade เป็น action หลัก (`:442`–`:635`)
4. **เพิ่มระดับการอ่าน:** ใช้ 14–16px สำหรับชื่อ/ตัวเลขที่ต้องตัดสินใจ และ 12–13px สำหรับ metadata; ลด uppercase และ monospace ในข้อความอธิบาย เก็บ monospace/tabular numbers สำหรับตัวเลข (`:444`, `:1064`)
5. **มือถือใช้ card/list ที่คงข้อมูลสำคัญ:** table ใช้ horizontal scroll ได้ แต่ไม่ควรต้องเลื่อนหลายคอลัมน์เพื่อเห็น Value/P&L/Action; execution row ปัจจุบันเป็น flex แถวเดียว มี gap และ min-width ควร stack หรือย่อ metadata (`:440`, `:1050`)
6. **ให้ return navigation จำบริบท:** activeTab, news filters, page และ sort ส่วนมากเป็น local refs; อ่านข่าวแล้ว Back to Market Intelligence กลับ `/portfolio` และเปิด Holdings ใหม่ ควรเก็บ tab/filter ใน URL หรือ state ที่คืนกลับได้ (`PortfolioView.vue:1199`; `NewsDetailView.vue` function backToNews)
7. **ทำฟอร์มบันทึกให้ตรวจทานง่าย:** สรุป Buy/Sell/Dividend + asset + target portfolio + trade currency + local timestamp + net amount ก่อน Save; quote ที่ prefill ต้องระบุว่าเป็นราคาตลาดเพื่ออ้างอิง ให้ผู้ใช้ยืนยันราคาที่ execute จริง
8. **รองรับ keyboard เป็นส่วนหนึ่งของตาราง/ฟอร์ม:** sort headers เป็น th ที่มี click แต่ไม่มี button/aria-sort; autocomplete มี Escape แต่ไม่มี arrow navigation; modal ไม่มี focus management/dialog semantics ควรแก้เป็น shared components เพื่อให้ flow เหมือนกันทั้งหมด

## ลำดับลงมือที่แนะนำ

1. แก้ F01–F08 ก่อน: scope, identity, currency และ write feedback ต้องตรงกันทุกหน้า
2. แก้ F09–F16 พร้อมกำหนด loading/empty/error/stale เป็นมาตรฐานร่วม
3. ปรับข้อมูลและ action hierarchy ก่อนเปลี่ยนสีหรือเพิ่ม animation
4. ตรวจ flow ครบวงจรด้วยข้อมูลอย่างน้อยสองพอร์ตที่ถือ ticker เดียวกัน, สินทรัพย์ THB/USD, buy/sell/dividend, fractional shares, และ quote ที่ไม่พร้อมใช้งาน

## กรณีตรวจรับรวม

- พอร์ต A และ B ถือ ticker เดียวกัน: หน้ารวม/รายละเอียด/Max Sell/Trade/Move ต้องอ้าง holding เดียวกัน
- เลือก Crypto + พอร์ต A + USD แล้ว manual refresh และ polling: ตัวกรองกับผลรวมไม่เปลี่ยน scope
- เปลี่ยน display currency: ตัวเลขทุกช่องแปลงจริงและไม่แก้ trade/holding currency
- บันทึก POST สำเร็จแต่ refresh ข่าวล้มเหลว: ไม่แจ้งว่าบันทึกล้มเหลวและไม่เกิดรายการซ้ำ
- เปิด edit แล้ว Save โดยไม่แก้ค่า: timestamp, portfolio, currency และ amount เดิมทุกช่อง
- Sell และ Dividend มี fee/tax: net amount ตรงกันใน modal, executions และ asset detail
- Buy จาก Watchlist และเพิ่ม Watchlist ซ้ำ: ไม่ต้องค้นสินทรัพย์เดิมใหม่ และรายการไม่ถูกลบ
- Provider ล่ม/timeframe request ล้มเหลว: แสดง error/stale ที่ตรงจริงโดยไม่สวมป้ายใหม่ให้ข้อมูลเก่า
- ย้าย holding ที่ปลายทางมี ticker เดิม: UI อธิบาย merge และ update metadata ต่อได้โดยไม่อ้าง source id ที่ถูกลบ

