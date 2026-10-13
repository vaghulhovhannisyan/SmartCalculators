const API = "http://localhost:8080";

async function post(path, body){
  const r = await fetch(API + path, {
    method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify(body)
  });
  if(!r.ok) throw new Error(await r.text());
  return r.json();
}

async function calcGeneral(){
  const box = document.getElementById("generalResult");
  box.textContent = "Расчёт…";
  try{
    const d = await post("/api/calc/general", {
      area: +document.getElementById("area").value,
      height: +document.getElementById("height").value,
      object_type: document.getElementById("objectType").value,
      repair_type: document.getElementById("repairType").value
    });
    box.innerHTML = d.lines.map(l =>
      `<div class="line"><span>${l.item} <span class="badge">${l.category}</span></span>
       <span>${l.qty} ${l.unit} · ${l.total.toLocaleString("ru")} ₽</span></div>`
    ).join("") +
    `<div class="line total"><span>Работы</span>
      <span>${d.labor_total.toLocaleString("ru")} ₽</span></div>
     <div class="line total"><span>Итого</span>
      <span>${d.grand_total.toLocaleString("ru")} ₽</span></div>`;
  }catch(e){ box.textContent = "Ошибка: " + e.message; }
}

async function calcRoom(){
  const box = document.getElementById("roomResult");
  box.textContent = "Подбор…";
  try{
    const d = await post("/api/calc/room", {
      area: +document.getElementById("roomArea").value,
      room_type: document.getElementById("roomType").value,
      humidity: +document.getElementById("humidity").value,
      load: document.getElementById("load").value
    });
    box.innerHTML = d.lines.slice(0,6).map(l =>
      `<div class="line"><span>${l.item} <span class="badge">${l.category}</span></span>
       <span>score ${l.recommend_score.toFixed(2)}</span></div>`
    ).join("") +
    `<div class="line total"><span>Итого</span>
      <span>${d.grand_total.toLocaleString("ru")} ₽</span></div>`;
  }catch(e){ box.textContent = "Ошибка: " + e.message; }
}

async function calcProduct(){
  const box = document.getElementById("productResult");
  box.textContent = "Расчёт…";
  try{
    const d = await post("/api/calc/product", {
      product_type: document.getElementById("productType").value,
      width: +document.getElementById("pWidth").value,
      height: +document.getElementById("pHeight").value
    });
    box.innerHTML = `<div class="line total">
      <span>Нужно</span><span>${d.qty} ${d.unit}</span></div>`;
  }catch(e){ box.textContent = "Ошибка: " + e.message; }
}