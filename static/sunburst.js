
var width = 500,
    height = 500,
    radius = Math.min(width, height) / 2;

var x = d3.scale.linear()
    .range([0, 2 * Math.PI]);

var y = d3.scale.sqrt()
    .range([0, radius]);

var svg = d3.select("div#chart").append("svg")
    .attr("width", width)
    .attr("height", height)
    .append("g")
    .attr("transform", "translate(" + width / 2 + "," + (height / 2 + 10) + ")");

var partition = d3.layout.partition()
    .value(function(d) { return d.size; });

var arc = d3.svg.arc()
    .startAngle(function(d) { return Math.max(0, Math.min(2 * Math.PI, x(d.x))); })
    .endAngle(function(d) { return Math.max(0, Math.min(2 * Math.PI, x(d.x + d.dx))); })
    .innerRadius(function(d) { return Math.max(0, y(d.y)); })
    .outerRadius(function(d) { return Math.max(0, y(d.y + d.dy)); });

d3.json(json_filename, function(error, root) {
  var path = svg.selectAll("path")
      .data(partition.nodes(root))
      .enter().append("path")
      .attr("d", arc)
      // Set colour based on whether element has children.
      .style("fill", function(d) { return (d.children ? "#00A2FF" : "#BFE5FF"); })
      .on("click", click)
      .on("mouseover", mouseover)
      .on("mouseout", mouseout);

  function click(d) {
    console.log("You clicked:");
    console.log(d);
    path.transition()
      .duration(750)
      .attrTween("d", arcTween(d));
  }

  function mouseover(d) {
    //console.log("You are hovering over: " + d.name);
    d3.select("p#path").text(d.name);
  }

  function mouseout(d) {
    d3.select("p#path").text("...");
  }
});

d3.select(self.frameElement).style("height", height + "px");

// Interpolate the scales!
function arcTween(d) {
  var xd = d3.interpolate(x.domain(), [d.x, d.x + d.dx]),
      yd = d3.interpolate(y.domain(), [d.y, 1]),
      yr = d3.interpolate(y.range(), [d.y ? 20 : 0, radius]);
  return function(d, i) {
    return i
        ? function(t) { return arc(d); }
        : function(t) { x.domain(xd(t)); y.domain(yd(t)).range(yr(t)); return arc(d); };
  };
}