import plotly.graph_objects as go

# Manually input the data as Python lists
dates = ['2020-11-25', '2020-12-09', '2020-12-25', '2021-02-23', '2021-05-26', '2021-11-25']
va_od = [0.05,0.05,0.2,0.5,0.7,0.8]
va_os = [1.0,0.9,1.0,0.8,0.9,0.8]
cmt_od = [642,730,650,462,370,361]
cmt_os = [280, 267,270,265,262, 265]

# Create a line plot with two y-axes
fig = go.Figure()

# Add the line plot for measurementA
fig.add_trace(
    go.Line(
        x=dates, 
        y=va_od, 
        name='VA_OD', 
        # line=dict(color='blue')
    )
)

fig.add_trace(
    go.Line(
        x=dates, 
        y=va_os, 
        name='VA_OS', 
        # line=dict(color='blue')
    )
)

# Add the line plot for measurementB
fig.add_trace(
    go.Line(
        x=dates,
        y=cmt_od,
        name='CMT_OD',
        # line=dict(color='red'),
        yaxis='y2'
    )
)

# Add the line plot for measurementB
fig.add_trace(
    go.Line(
        x=dates,
        y=cmt_os,
        name='CMT_OS',
        # line=dict(color='red'),
        yaxis='y2'
    )
)

# Set the title and axis labels
fig.update_layout(
    # title='Measurement A and B over Time',
    xaxis=dict(
        title='Date',
        tickmode='linear',
        dtick='M1',  # Adjust the spacing between ticks here (M1 indicates monthly spacing)
        tickformat='%Y-%m-%d'),  # Custom tick label format (abbreviated month and year)
    yaxis=dict(title='VA', color='blue'),
    yaxis2=dict(title='CMT', color='red', overlaying='y', side='right'),
    hovermode='x unified',
    xaxis_hoverformat='%Y-%m-%d',
)

fig.update_xaxes(showspikes=True, showline=False, spikedash='dash', showticklabels = True)


# Add vertical lines and annotations
vertical_lines = ['2020-11-25', '2021-01-02']
annotations = ['IVIO OD', 'IVIE OD']

for i in range(len(vertical_lines)):
    fig.add_shape(
        type='line',
        x0=vertical_lines[i],
        x1=vertical_lines[i],
        y0=0,
        y1=1,
        xref='x',
        yref='paper',
        line=dict(color='black', dash='dash'),
        name=f'Event {i+1}',
        # hovertemplate=f'<b>Event {i+1}</b><br>Date: {vertical_lines[i]}'
    )
    fig.add_trace(go.Scatter(x=[vertical_lines[i], vertical_lines[i]], y=[0, 1], mode='lines',
                             line=dict(color='black', dash='dash'),
                             name=annotations[i],
                             hovertemplate=f'Date: {vertical_lines[i]}',showlegend=False))

    fig.add_annotation(x=vertical_lines[i], y=1.1, xref='x', yref='paper',
                    text=annotations[i], showarrow=False)

# Show the plot
fig.show()