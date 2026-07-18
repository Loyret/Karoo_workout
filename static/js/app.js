function drawWorkoutChart(data) {
    const ctx = document.getElementById('previewChart') ||
                document.getElementById('workoutChart');
    if (!ctx) return;

    if (ctx._chartInstance) {
        ctx._chartInstance.destroy();
    }

    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: '% FTP',
                    data: data.powers,
                    backgroundColor: data.colors.map(c => c + 'cc'),
                    borderColor: data.colors,
                    borderWidth: 1,
                    borderRadius: 2,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1e293b',
                    titleColor: '#e2e8f0',
                    bodyColor: '#94a3b8',
                    borderColor: '#334155',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        title: function(items) {
                            const idx = items[0].dataIndex;
                            return `Время: ${data.labels[idx]}`;
                        },
                        label: function(item) {
                            const idx = item.dataIndex;
                            const parts = [`${item.raw}% FTP`];
                            if (data.cadences[idx]) {
                                parts.push(`${data.cadences[idx]} rpm`);
                            }
                            return parts;
                        },
                        afterLabel: function(item) {
                            const idx = item.dataIndex;
                            return data.texts[idx] || '';
                        },
                    },
                },
            },
            scales: {
                x: {
                    display: true,
                    grid: { display: false },
                    ticks: {
                        color: '#64748b',
                        maxRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: 15,
                        font: { size: 11 },
                    },
                },
                y: {
                    display: true,
                    beginAtZero: true,
                    max: 200,
                    grid: {
                        color: 'rgba(51, 65, 85, 0.5)',
                        drawBorder: false,
                    },
                    ticks: {
                        color: '#64748b',
                        callback: v => v + '%',
                        font: { size: 11 },
                    },
                    title: {
                        display: true,
                        text: '% FTP',
                        color: '#64748b',
                    },
                },
            },
        },
    });

    ctx._chartInstance = chart;
}
