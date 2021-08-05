
function validateForm() {
  const query = document.getElementById("search").value
  console.log(query)
  if (query.split(" ").length <= 1) {
    alert("Please search with more than one word.")
    return false
  }
  else {
    document.getElementByClass("search-form").submit()
  }
}


function menuHandler() {
  // alert("beibi")
  if (document.getElementById("menu-links").style.right === "0px") {
    document.getElementById("menu-links").style.right = "-250px"
  }
  else {
    document.getElementById("menu-links").style.right = "0px"

  }
}
