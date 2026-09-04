import 'package:flutter/material.dart';

enum MetricChartType { line, bars }

class MetricChart extends StatelessWidget {
  const MetricChart({
    required this.values,
    required this.color,
    this.secondary,
    this.secondaryColor,
    this.type = MetricChartType.line,
    super.key,
  });
  final List<double> values;
  final Color color;
  final List<double>? secondary;
  final Color? secondaryColor;
  final MetricChartType type;
  @override
  Widget build(BuildContext context) => CustomPaint(
    painter: _ChartPainter(values, color, secondary, secondaryColor, type),
    child: const SizedBox.expand(),
  );
}

class _ChartPainter extends CustomPainter {
  const _ChartPainter(
    this.values,
    this.color,
    this.secondary,
    this.secondaryColor,
    this.type,
  );
  final List<double> values;
  final Color color;
  final List<double>? secondary;
  final Color? secondaryColor;
  final MetricChartType type;
  @override
  void paint(Canvas canvas, Size size) {
    final grid = Paint()
      ..color = const Color(0xFF293244)
      ..strokeWidth = 1;
    for (var i = 1; i < 5; i++) {
      final y = size.height * i / 5;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), grid);
    }
    type == MetricChartType.bars
        ? _bars(canvas, size, values, color)
        : _line(canvas, size, values, color);
    if (secondary != null) {
      _line(canvas, size, secondary!, secondaryColor ?? Colors.green);
    }
  }

  void _line(Canvas canvas, Size size, List<double> data, Color shade) {
    if (data.length < 2) return;
    final minimum = data.reduce((a, b) => a < b ? a : b);
    final maximum = data.reduce((a, b) => a > b ? a : b);
    final spread = maximum == minimum ? 1.0 : maximum - minimum;
    final path = Path();
    for (var i = 0; i < data.length; i++) {
      final p = Offset(
        i * size.width / (data.length - 1),
        size.height * (1 - ((data[i] - minimum) / spread)),
      );
      i == 0 ? path.moveTo(p.dx, p.dy) : path.lineTo(p.dx, p.dy);
    }
    canvas.drawPath(
      path,
      Paint()
        ..color = shade
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2,
    );
  }

  void _bars(Canvas canvas, Size size, List<double> data, Color shade) {
    if (data.isEmpty) return;
    final maximum = data.reduce((a, b) => a > b ? a : b);
    final scale = maximum <= 0 ? 1.0 : maximum;
    final gap = 8.0;
    final width = (size.width - gap * (data.length + 1)) / data.length;
    for (var i = 0; i < data.length; i++) {
      canvas.drawRRect(
        RRect.fromRectAndRadius(
          Rect.fromLTWH(
            gap + i * (width + gap),
            size.height * (1 - data[i] / scale),
            width,
            size.height * data[i] / scale,
          ),
          const Radius.circular(3),
        ),
        Paint()..color = shade,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _ChartPainter old) =>
      old.values != values || old.secondary != secondary || old.color != color;
}
