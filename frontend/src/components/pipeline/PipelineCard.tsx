import { Card, Text, Badge, Group } from '@mantine/core'
import { IconMessage } from '@tabler/icons-react'
import { Draggable } from '@hello-pangea/dnd'
import dayjs from 'dayjs'

interface PipelineCardProps {
  entry: any
  index: number
  onClick: () => void
}

export default function PipelineCard({ entry, index, onClick }: PipelineCardProps) {
  const opp = entry.opportunity

  return (
    <Draggable draggableId={entry.id} index={index}>
      {(provided, snapshot) => (
        <Card
          ref={provided.innerRef}
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          shadow={snapshot.isDragging ? 'md' : 'xs'}
          padding="sm"
          radius="sm"
          withBorder
          onClick={onClick}
          style={{
            ...provided.draggableProps.style,
            cursor: 'pointer',
            opacity: snapshot.isDragging ? 0.9 : 1,
          }}
        >
          <Text size="sm" fw={500} lineClamp={2}>
            {opp?.title || 'Opportunity'}
          </Text>

          {opp?.agency && (
            <Text size="xs" c="dimmed" mt={2} lineClamp={1}>
              {opp.agency}
            </Text>
          )}

          <Group mt="xs" gap={4} wrap="wrap">
            {opp?.analysis?.relevancy_score != null && (
              <Badge
                size="xs"
                variant="light"
                color={
                  opp.analysis.relevancy_score >= 70 ? 'green' :
                  opp.analysis.relevancy_score >= 40 ? 'yellow' : 'red'
                }
              >
                {opp.analysis.relevancy_score}%
              </Badge>
            )}
            {opp?.response_deadline && (
              <Badge size="xs" variant="light" color="orange">
                {dayjs(opp.response_deadline).format('MMM D')}
              </Badge>
            )}
            <Badge size="xs" variant="outline">P{entry.priority}</Badge>
            {entry.comment_count > 0 && (
              <Badge size="xs" variant="light" color="gray" leftSection={<IconMessage size={10} />}>
                {entry.comment_count}
              </Badge>
            )}
          </Group>
        </Card>
      )}
    </Draggable>
  )
}
