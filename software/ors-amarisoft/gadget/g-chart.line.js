function LineChart(container, data, label, tooltip) {
	this.container = container;
	this.context = this.container.getContext("2d");
	
	this.data = data;
	this.label = label;
	this.tooltip = tooltip;
	
	this.point_radius = 5;
	
	this.data_length = this.data.length;
	this.data_max = this.getMax();
	this.data_min = this.getMin();
	
	this.width = this.container.width;
	this.height = this.container.height;
	
	this.x_padding = this.width  * 0.1;
	this.y_padding = this.height * 0.1;
	this.x_step    = ( this.width - this.x_padding )     / this.data_length;
	this.y_grid_steps = 10;
	this.y_step    = ( this.height - this.y_padding * 2) / this.y_grid_steps
	
	this.coordinates = [];
}
LineChart.prototype = {
	constructor: LineChart,
	tooltipOn: function (which) {
		if(which === 'click')
			this.container.addEventListener('click', this.clickEvent.bind(this));
		else if(which === 'mousemove')
			this.container.addEventListener('mousemove', this.hoverEvent.bind(this));
		else 
			console.log('Tooltip activation method not supported');
	},
	prepareData: function () {
		for(var i = 0 ; i < this.data_length ; i++) {
			this.coordinates.push({
				x: this.calcCoordinateX(i),
				y: this.calcCoordinateY(i)
			});
		}
	},
	draw: function () {
		this.drawBorder();
		this.prepareData();
		this.drawGrid();
		
		var coordinates = [];
		for(var i = 0 ; i < this.data_length -1; i++) {
			coordinates = this.getLineCoordinates(i);
			
			this.drawLine(coordinates, '#16D', 0);
			this.drawPoint(coordinates[0], '#16D');
		}
		this.drawPoint(coordinates[1]);
	},
	drawBorder: function () {
		this.drawLine([{x:0,y:0},{x:this.width, y:0}],'#000', 0);
		this.drawLine([{x:this.width, y:0},{x:this.width, y:this.height}],'#000', 0);
		this.drawLine([{x:this.width, y:this.height},{x:0, y:this.height}],'#000', 0);
		this.drawLine([{x:0, y:this.height},{x:0,y:0}],'#000', 0);
	},
	drawGrid: function () {		
		// Horizontal lines
		for(var i = 0 ; i <= this.y_grid_steps ; i++) {
			this.drawLine([
				{ x: this.x_padding/2, 							y: this.y_step * i + this.y_padding }, 
				{ x: this.width - this.x_padding/2, y: this.y_step * i + this.y_padding }], 
			'#DDD', 0);
		}
		
		// Vertical left line
		this.drawLine([
				{ x: this.x_padding/2, y: this.y_padding }, 
				{ x: this.x_padding/2, y: this.height - this.y_padding }], 
			'#DDD', 0);
		
		// Vertical dashed lines
		for(var i = 0 ; i <= this.data_length ; i++) {
			this.drawLine([
				{ x: this.x_step * i + this.x_padding, y: this.y_padding }, 
				{ x: this.x_step * i + this.x_padding, y: this.height - this.y_padding }], 
			'#DDD', 5);
		}
		
		// Draw label
		this.drawLabel();
	},
	drawLabel: function () {
		for (var i = 0 ; i <= this.y_grid_steps ; i++) {
			this.drawText(
				{ 
					x: this.x_padding / 4, 
					y: this.y_step * i + this.y_padding 
				}, this.getLabelY(i)
			);
		}
		for (var i = 0 ; i < this.data_length ; i++) {
			this.drawText(
				{ 
					x: this.getCoordinate(i).x,
					y: this.height - this.y_padding / 2
				}, this.getLabelX(i)
			);
		}
	},
	drawLine: function (coordinates, style, dash) {
		this.context.setLineDash([dash]);
		this.context.beginPath();
		this.context.moveTo(coordinates[0].x,coordinates[0].y);
		this.context.lineTo(coordinates[1].x,coordinates[1].y);
		this.context.strokeStyle = style;
		this.context.stroke();
	},
	drawPoint: function (coordinate, style) {
		this.context.beginPath();
		this.context.arc(coordinate.x, coordinate.y, this.point_radius, 0, 2 * Math.PI, false);
		this.context.fillStyle = '#FFF';
		this.context.fill();
		this.context.strokeStyle = style;
		this.context.stroke();
	},
	drawText: function (coordinate, text) {
		this.context.fillStyle    = '#AAA';
		this.context.textBaseline = 'middle';
		this.context.textAlign    = 'center'; 
		this.context.fillText(text, coordinate.x, coordinate.y);
	},
	calcCoordinateX: function (index) {
		return this.x_step * index + this.x_padding;
	},
	calcCoordinateY: function (index) {
		var proportion = this.data[index] / this.data_max;
		var top_without_padding = proportion * ( this.height - this.y_padding * 2 );
		return this.height - ( top_without_padding + this.y_padding );
	},
	getLineCoordinates: function (i) {
		return [
			this.getCoordinate(i),
			this.getCoordinate(i + 1)
		];
	},
	getCoordinate: function (i) {
		return this.coordinates[i];
	},
	getMax: function () {
		var max = this.data[0];
		for (var i = 1 ; i < this.data_length ; i++)
			if(this.data[i] > max) max = this.data[i];
		return max;
	},
	getMin: function () {
		var min = this.data[0];
		for (var i = 1 ; i < this.data_length ; i++)
			if(this.data[i] < min) min = this.data[i];
		return min;
	},
	getLabelY: function (index) {
		return ((this.data_max / this.y_grid_steps) * ( this.y_grid_steps - index)).toFixed(1).replace(/[.,]0$/, "");
	},
	getLabelX: function (index) {
		return this.label[index];
	},
	
	distanceBetweenTwoPoints: function (coordinates) {
		return Math.sqrt(
			Math.pow( (coordinates[0].x - coordinates[1].x) , 2) +
			Math.pow( (coordinates[0].y - coordinates[1].y) , 2)
		);
	},
	getPointSelected: function (x, y) {
		for(var i = 0 ; i < this.data_length ; i++) {
			var coordinates = [
				{x: x, y: y},
				{x: this.coordinates[i].x, y: this.coordinates[i].y}
			];
			var dist = this.distanceBetweenTwoPoints(coordinates);
		
			if (dist <= this.point_radius + 1) {
				 return i;
			}
		}
		console.log('None');
		return null;
	},
	
	clickEvent: function (event) {
		var point = this.getPointSelected(event.layerX, event.layerY);
		
		if(point != null) {
			this.showTooltip(this.tooltip[point], { x: event.clientX, y: event.clientY});
		} else {
			this.removeTooltip();
		}
	},
	hoverEvent: function (event) {
		var point = this.getPointSelected(event.layerX, event.layerY);
		
		if(point != null) {
			this.showTooltip(this.tooltip[point], { x: event.clientX, y: event.clientY});
		} else {
			this.removeTooltip();
		}
	},
	
	showTooltip: function (text, coordinate) {
		var tooltip = document.getElementById('tooltip');
		if(tooltip) {
			tooltip.style.top = coordinate.y + 'px';
			tooltip.style.left = coordinate.x + 'px';
			tooltip.innerHTML = text;
		} else {
			tooltip = document.createElement('div');
			tooltip.setAttribute('id', 'tooltip');
			tooltip.classList.add('tooltip-chart');
			tooltip.style.top = coordinate.y + 'px';
			tooltip.style.left = coordinate.x + 'px';
			tooltip.innerHTML = text;
			this.container.parentNode.appendChild(tooltip);
		}
	},
	removeTooltip: function () {
		var tooltip = document.getElementById('tooltip');
		if(tooltip)
			this.container.parentNode.removeChild(tooltip);
	}
};