// 测试路由跳转逻辑
// 这个脚本用于在浏览器控制台中运行，测试路由跳转

console.log("=== 路由跳转测试 ===");

// 模拟row对象
const testRow = {
  id: 1,
  name: "测试客户",
  phone: "13800138000"
};

console.log("测试row对象:", testRow);
console.log("row.id:", testRow.id, "typeof row.id:", typeof testRow.id);

// 模拟路由跳转
const customerId = parseInt(testRow.id);
console.log("解析后的customerId:", customerId);

const targetPath = `/customer/detail/${customerId}`;
console.log("目标路径:", targetPath);

// 检查路径格式
if (targetPath.includes(':id')) {
  console.error("❌ 路径包含字面量 :id，说明ID没有被正确传递");
} else {
  console.log("✅ 路径格式正确，包含实际ID值");
}

// 检查路由是否已注册（需要在浏览器中运行）
if (typeof window !== 'undefined' && window.$router) {
  try {
    const route = window.$router.resolve(targetPath);
    console.log("路由解析结果:", route);
    if (route.name) {
      console.log("✅ 路由已注册，名称:", route.name);
    } else {
      console.warn("⚠️ 路由可能未注册");
    }
  } catch (err) {
    console.error("路由解析失败:", err);
  }
}
























