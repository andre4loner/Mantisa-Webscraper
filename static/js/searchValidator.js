
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